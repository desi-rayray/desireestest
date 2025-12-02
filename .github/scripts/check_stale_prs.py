#!/usr/bin/env python3
"""
Script to check for stale PRs and post notifications to Slack.
This script is designed to run in GitHub Actions and will:
1. Fetch all open PRs from the repository
2. Identify PRs that haven't been updated in X days (stale)
3. Determine CODEOWNERS for changed files
4. Post a formatted message to Slack with reviewer tags and CODEOWNERS
"""

import os
import sys
import json
import re
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Set, Tuple
from pathlib import Path


def get_github_api_headers() -> Dict[str, str]:
    """Get headers for GitHub API requests."""
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    
    return {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'stale-pr-checker'
    }


def get_repo_info() -> tuple[str, str]:
    """Extract repository owner and name from GitHub Actions environment."""
    # In GitHub Actions, GITHUB_REPOSITORY is in format "owner/repo"
    repo = os.environ.get('GITHUB_REPOSITORY')
    if not repo:
        raise ValueError("GITHUB_REPOSITORY environment variable is required")
    
    owner, repo_name = repo.split('/', 1)
    return owner, repo_name


def parse_codeowners() -> List[Tuple[str, List[str]]]:
    """
    Parse CODEOWNERS file and return list of (pattern, owners) tuples.
    Returns patterns in order (last match takes precedence).
    """
    codeowners_path = Path('.github/CODEOWNERS')
    if not codeowners_path.exists():
        print("Warning: CODEOWNERS file not found at .github/CODEOWNERS", file=sys.stderr)
        return []
    
    rules = []
    with open(codeowners_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            # Remove comments
            line = line.split('#')[0].strip()
            if not line:
                continue
            
            # Split pattern and owners
            parts = line.split()
            if len(parts) < 2:
                continue
            
            pattern = parts[0]
            owners = parts[1:]
            rules.append((pattern, owners))
    
    return rules


def match_codeowners_pattern(pattern: str, file_path: str) -> bool:
    """
    Check if a file path matches a CODEOWNERS pattern.
    Supports basic glob patterns like *, **, and path prefixes.
    """
    # Convert CODEOWNERS pattern to regex
    # * matches any characters except /
    # ** matches any characters including /
    # / at start means root of repo
    
    # Escape special regex chars except * and /
    regex_pattern = re.escape(pattern)
    
    # Replace escaped \*\* with .* (matches anything)
    regex_pattern = regex_pattern.replace(r'\*\*', '.*')
    # Replace escaped \* with [^/]* (matches anything except /)
    regex_pattern = regex_pattern.replace(r'\*', '[^/]*')
    
    # If pattern starts with /, anchor to start
    if pattern.startswith('/'):
        regex_pattern = '^' + regex_pattern
    else:
        # Otherwise match anywhere
        regex_pattern = '.*' + regex_pattern
    
    # Ensure it matches the full path or ends with the pattern
    if not regex_pattern.endswith('$'):
        regex_pattern += '$'
    
    try:
        return bool(re.match(regex_pattern, file_path))
    except re.error:
        # If regex fails, do simple string matching
        if pattern.startswith('/'):
            return file_path.startswith(pattern[1:])  # Remove leading /
        return pattern in file_path


def get_codeowners_for_files(changed_files: List[str], codeowners_rules: List[Tuple[str, List[str]]]) -> Set[str]:
    """
    Determine CODEOWNERS for a list of changed files.
    Returns a set of owner identifiers (users and teams).
    """
    owners = set()
    
    # Check each file against CODEOWNERS rules (in order, last match wins)
    for file_path in changed_files:
        # Normalize file path (remove leading / if present)
        normalized_path = file_path.lstrip('/')
        
        # Find matching rule (last match takes precedence per CODEOWNERS spec)
        matched_owners = []
        for pattern, pattern_owners in codeowners_rules:
            if match_codeowners_pattern(pattern, normalized_path):
                matched_owners = pattern_owners
        
        owners.update(matched_owners)
    
    return owners


def get_pr_files(owner: str, repo: str, pr_number: int) -> List[str]:
    """Get list of files changed in a PR."""
    headers = get_github_api_headers()
    url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files'
    params = {'per_page': 100}
    
    all_files = []
    page = 1
    
    while True:
        params['page'] = page
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            files = response.json()
            if not files:
                break
            
            all_files.extend([f.get('filename') for f in files if f.get('filename')])
            page += 1
            
            if len(files) < 100:
                break
        except requests.exceptions.RequestException as e:
            print(f"Warning: Could not fetch files for PR #{pr_number}: {e}", file=sys.stderr)
            break
    
    return all_files


def map_github_to_slack(github_owner: str, slack_mapping: Dict[str, str]) -> str:
    """
    Map a GitHub owner (user or team) to Slack mention format.
    Returns Slack mention string.
    """
    # Remove @ if present
    owner_key = github_owner.lstrip('@')
    
    # Check if there's a direct mapping
    if owner_key in slack_mapping:
        slack_id = slack_mapping[owner_key]
        # If it's already a Slack ID format, return as-is
        if slack_id.startswith('<!subteam^') or slack_id.startswith('<@'):
            return slack_id
        # Otherwise assume it's a user group name
        return f'<!subteam^{slack_id}|{owner_key}>'
    
    # Check for team format (org/team-name)
    if '/' in owner_key:
        org, team = owner_key.split('/', 1)
        # Try mapping the team name
        if team in slack_mapping:
            slack_id = slack_mapping[team]
            if slack_id.startswith('<!subteam^') or slack_id.startswith('<@'):
                return slack_id
            return f'<!subteam^{slack_id}|{team}>'
        # Fallback: try to format as Slack group mention
        # Convert team-name to team_name format
        team_slug = team.lower().replace('-', '_')
        return f'<!subteam^ID|{team_slug}>'  # Placeholder format
    
    # For individual users, try to mention them
    # This assumes GitHub username matches Slack username (may need adjustment)
    return f'<@{owner_key}>'


def fetch_open_prs(owner: str, repo: str) -> List[Dict]:
    """Fetch all open pull requests from the repository."""
    headers = get_github_api_headers()
    url = f'https://api.github.com/repos/{owner}/{repo}/pulls'
    params = {'state': 'open', 'sort': 'updated', 'direction': 'desc', 'per_page': 100}
    
    all_prs = []
    page = 1
    
    while True:
        params['page'] = page
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        prs = response.json()
        if not prs:
            break
        
        all_prs.extend(prs)
        page += 1
        
        # GitHub API limits to 100 items per page
        if len(prs) < 100:
            break
    
    return all_prs


def get_pr_reviewers(owner: str, repo: str, pr_number: int) -> List[Dict]:
    """Get requested reviewers for a PR."""
    headers = get_github_api_headers()
    url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers'
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        reviewers = []
        # Get user reviewers
        for user in data.get('users', []):
            reviewers.append({
                'login': user.get('login'),
                'type': 'user'
            })
        
        # Get team reviewers
        for team in data.get('teams', []):
            reviewers.append({
                'login': team.get('slug'),
                'type': 'team'
            })
        
        return reviewers
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not fetch reviewers for PR #{pr_number}: {e}", file=sys.stderr)
        return []


def is_pr_stale(pr: Dict, stale_hours: float) -> bool:
    """Check if a PR is stale based on last update time."""
    updated_at_str = pr.get('updated_at')
    if not updated_at_str:
        return False
    
    updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    time_since_update = now - updated_at
    hours_since_update = time_since_update.total_seconds() / 3600
    
    return hours_since_update >= stale_hours


def format_slack_message(stale_prs: List[Dict], stale_hours: float, repo_name: str, owner: str, repo: str, codeowners_rules: List[Tuple[str, List[str]]], slack_mapping: Dict[str, str]) -> Dict:
    """Format the message to send to Slack."""
    if not stale_prs:
        return {
            'text': f'✅ No stale PRs found in {repo_name}! All PRs are up to date.',
            'blocks': [
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': f'✅ *No stale PRs found in {repo_name}!*\nAll PRs are up to date.'
                    }
                }
            ]
        }
    
    blocks = [
        {
            'type': 'header',
            'text': {
                'type': 'plain_text',
                'text': f'⚠️ Stale PRs Alert ({len(stale_prs)} found)'
            }
        },
        {
            'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'Found *{len(stale_prs)}* PR{"s" if len(stale_prs) != 1 else ""} in `{repo_name}` that {"have" if len(stale_prs) != 1 else "has"} not been updated in {stale_hours}+ hours.'
                }
        },
        {
            'type': 'divider'
        }
    ]
    
    for pr in stale_prs:
        pr_number = pr.get('number')
        title = pr.get('title', 'Untitled')
        html_url = pr.get('html_url')
        author = pr.get('user', {}).get('login', 'Unknown')
        updated_at_str = pr.get('updated_at', '')
        
        # Calculate hours stale
        if updated_at_str:
            updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            time_since_update = now - updated_at
            hours_stale = time_since_update.total_seconds() / 3600
        else:
            hours_stale = stale_hours
        
        # Get reviewers
        reviewers = get_pr_reviewers(owner, repo, pr_number)
        
        # Format reviewer mentions
        reviewer_mentions = []
        if reviewers:
            for reviewer in reviewers:
                if reviewer['type'] == 'user':
                    reviewer_mentions.append(f'<@{reviewer["login"]}>')
                elif reviewer['type'] == 'team':
                    reviewer_mentions.append(f'@{reviewer["login"]}')
        
        reviewer_text = ', '.join(reviewer_mentions) if reviewer_mentions else 'No reviewers assigned'
        
        # Get CODEOWNERS for changed files
        codeowners_mentions = []
        if codeowners_rules:
            try:
                changed_files = get_pr_files(owner, repo, pr_number)
                codeowners = get_codeowners_for_files(changed_files, codeowners_rules)
                
                if codeowners:
                    for owner_id in sorted(codeowners):
                        slack_mention = map_github_to_slack(owner_id, slack_mapping)
                        codeowners_mentions.append(slack_mention)
            except Exception as e:
                print(f"Warning: Could not determine CODEOWNERS for PR #{pr_number}: {e}", file=sys.stderr)
        
        codeowners_text = ', '.join(codeowners_mentions) if codeowners_mentions else 'No CODEOWNERS found'
        
        # Build PR block
        # Add warning emoji if no reviewers
        warning_prefix = '🚨 ' if not reviewers else ''
        pr_text = f'{warning_prefix}*<{html_url}|PR #{pr_number}: {title}>*\n'
        # Format hours nicely - show days if >= 24 hours, otherwise show hours
        if hours_stale >= 24:
            days = int(hours_stale // 24)
            remaining_hours = int(hours_stale % 24)
            if remaining_hours > 0:
                stale_text = f'{days}d {remaining_hours}h'
            else:
                stale_text = f'{days}d'
        else:
            stale_text = f'{int(hours_stale)}h'
        pr_text += f'Author: `{author}` | Stale: *{stale_text}*\n'
        pr_text += f'Reviewers: {reviewer_text}\n'
        pr_text += f'CODEOWNERS: {codeowners_text}'
        
        blocks.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': pr_text
            }
        })
        
        blocks.append({
            'type': 'divider'
        })
    
    return {
        'text': f'Found {len(stale_prs)} stale PRs in {repo_name}',
        'blocks': blocks
    }


def post_to_slack(webhook_url: str, message: Dict) -> bool:
    """Post message to Slack via webhook."""
    try:
        response = requests.post(webhook_url, json=message, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error posting to Slack: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}", file=sys.stderr)
        return False


def load_slack_mapping() -> Dict[str, str]:
    """
    Load GitHub to Slack mapping from environment variable or file.
    Expected format: JSON string or path to JSON file.
    Example: {"Back-End": "S12345678", "Front-End": "S87654321", "jeffnb": "U12345678"}
    """
    # Try to load from environment variable (JSON string)
    mapping_json = os.environ.get('SLACK_TEAM_MAPPING')
    if mapping_json:
        try:
            return json.loads(mapping_json)
        except json.JSONDecodeError:
            print("Warning: SLACK_TEAM_MAPPING is not valid JSON, trying as file path", file=sys.stderr)
            # Try as file path
            mapping_path = Path(mapping_json)
            if mapping_path.exists():
                with open(mapping_path, 'r') as f:
                    return json.load(f)
    
    # Try default mapping file
    default_mapping_path = Path('.github/scripts/slack_team_mapping.json')
    if default_mapping_path.exists():
        with open(default_mapping_path, 'r') as f:
            return json.load(f)
    
    # Return empty mapping (will use fallback formatting)
    return {}


def main():
    """Main function to check for stale PRs and notify Slack."""
    # Get configuration from environment
    # Support both STALE_HOURS and STALE_DAYS for backward compatibility
    stale_hours = os.environ.get('STALE_HOURS')
    if stale_hours:
        stale_hours = float(stale_hours)
    else:
        stale_days = float(os.environ.get('STALE_DAYS', '3'))
        stale_hours = stale_days * 24  # Convert days to hours
    
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    
    if not webhook_url:
        print("Error: SLACK_WEBHOOK_URL environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    # Get repository info
    try:
        owner, repo_name = get_repo_info()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Checking for stale PRs in {owner}/{repo_name} (stale = {stale_hours}+ hours)...")
    
    # Parse CODEOWNERS
    codeowners_rules = parse_codeowners()
    print(f"Loaded {len(codeowners_rules)} CODEOWNERS rules")
    
    # Load Slack team mapping
    slack_mapping = load_slack_mapping()
    if slack_mapping:
        print(f"Loaded {len(slack_mapping)} Slack team mappings")
    else:
        print("Warning: No Slack team mapping found. CODEOWNERS will use fallback formatting.")
    
    # Fetch open PRs
    try:
        open_prs = fetch_open_prs(owner, repo_name)
        print(f"Found {len(open_prs)} open PRs")
    except Exception as e:
        print(f"Error fetching PRs: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Filter stale PRs
    stale_prs = [pr for pr in open_prs if is_pr_stale(pr, stale_hours)]
    
    print(f"Found {len(stale_prs)} stale PRs")
    
    # Format and send message
    message = format_slack_message(stale_prs, stale_hours, repo_name, owner, repo_name, codeowners_rules, slack_mapping)
    
    if post_to_slack(webhook_url, message):
        print("Successfully posted to Slack!")
    else:
        print("Failed to post to Slack", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

