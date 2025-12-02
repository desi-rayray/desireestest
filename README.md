# Stale PR Notifications Setup Guide

**Document Version**: 1.0  
**Last Updated**: December 2024  
**For**: IT/DevOps Team

## Overview

This guide provides step-by-step instructions for setting up automated stale PR notifications. The system includes:

- **GitHub Actions workflow** that runs weekly (or manually)
- **Slack integration** for posting notifications
- **CODEOWNERS detection** to automatically identify which team owns changed files
- **Team tagging** in Slack notifications

## Architecture

- **Workflow** (`.github/workflows/stale-pr-notifications.yml`)
  - Checks for stale PRs in the repository
  - Posts to Slack channel
  - Tags CODEOWNERS and reviewers

- **Python Script** (`.github/scripts/check_stale_prs.py`)
  - Fetches open PRs from GitHub
  - Determines staleness (configurable hours/days)
  - Formats and posts messages to Slack

## Prerequisites

- Admin access to the GitHub repository
- Access to create Slack apps and webhooks
- A Slack channel for notifications
- Basic understanding of GitHub Actions and Slack integrations

## Step 1: Create Slack Webhook

1. **Navigate to Slack Apps**:
   - Go to: https://api.slack.com/apps
   - Click **"Create New App"** → **"From scratch"**
   - **App Name**: `Stale PR Notifier`
   - **Workspace**: Select your workspace
   - Click **"Create App"**

2. **Enable Incoming Webhooks**:
   - In the left sidebar, click **"Incoming Webhooks"**
   - Toggle **"Activate Incoming Webhooks"** to **On**
   - Click **"Add New Webhook to Workspace"**
   - **Select Channel**: Choose your channel (e.g., `#engineering`, `#code-review`)
   - Click **"Allow"**

3. **Copy the Webhook URL**:
   - You'll see a webhook URL (it will start with `https://hooks.slack.com/services/`)
   - **Copy this entire URL** - you'll need it in Step 2
   - Save it securely (you won't be able to see it again)

## Step 2: Add Webhook URL to GitHub Secrets

1. **Navigate to Repository Settings**:
   - Go to: `https://github.com/YOUR_USERNAME/YOUR_REPO/settings/secrets/actions`
   - Replace `YOUR_USERNAME` and `YOUR_REPO` with your actual values
   - You must have admin access to the repository

2. **Add Webhook Secret**:
   - Click **"New repository secret"**
   - **Name**: `SLACK_WEBHOOK_URL`
   - **Secret**: Paste your webhook URL from Step 1
   - Click **"Add secret"**

**Security Note**: This secret is encrypted and only accessible to GitHub Actions workflows. Never commit webhook URLs to the repository.

## Step 3: Configure Staleness Threshold (Optional)

Set how long a PR must be inactive before it's considered stale.

1. **Navigate to Repository Variables**:
   - Go to: `https://github.com/YOUR_USERNAME/YOUR_REPO/settings/variables/actions`
   - Click **"Variables"** tab

2. **Add STALE_HOURS Variable**:
   - Click **"New repository variable"**
   - **Name**: `STALE_HOURS`
   - **Value**: Recommended values:
     - `2` = 2 hours (for quick testing)
     - `24` = 1 day
     - `72` = 3 days (default if not set)
     - `168` = 1 week
   - Click **"Add variable"**

**Note**: If `STALE_HOURS` is not set, the system defaults to `STALE_DAYS` (default: 3 days = 72 hours).

## Step 4: Set Up CODEOWNERS to Slack Group Mapping (Optional)

This enables automatic tagging of Slack user groups based on CODEOWNERS.

### Option A: Using a Mapping File (Recommended)

1. **Find Slack User Group IDs**:
   - In Slack, go to **Settings & administration** → **User groups**
   - Click on each user group you want to tag
   - The URL will contain the group ID: `https://yourworkspace.slack.com/usergroups/S12345678`
   - Copy the ID (the part after `/S`, e.g., `S12345678`)

2. **Create Mapping File**:
   - Copy the example: `cp .github/scripts/slack_team_mapping.json.example .github/scripts/slack_team_mapping.json`
   - Edit `.github/scripts/slack_team_mapping.json`:
     ```json
     {
       "Back-End": "S12345678",
       "Front-End": "S87654321",
       "Cloud": "S11223344"
     }
     ```
   - Replace with your actual Slack group IDs
   - Map GitHub team slugs (without `@org/` prefix) to Slack group IDs

3. **Commit the File**:
   ```bash
   git add .github/scripts/slack_team_mapping.json
   git commit -m "Add Slack team mapping for stale PR notifications"
   git push origin main
   ```

### Option B: Using Environment Variable

1. **Add Secret**:
   - Go to: `https://github.com/YOUR_USERNAME/YOUR_REPO/settings/secrets/actions`
   - Click **"New repository secret"**
   - **Name**: `SLACK_TEAM_MAPPING`
   - **Value**: JSON string like `{"Back-End": "S12345678", "Front-End": "S87654321"}`
   - Click **"Add secret"**

**Note**: If no mapping is provided, CODEOWNERS will still be detected but may not tag Slack groups properly.

## Step 5: Verify Workflow Files Exist

Ensure these files are in the repository:

- `.github/workflows/stale-pr-notifications.yml`
- `.github/scripts/check_stale_prs.py`
- `.github/CODEOWNERS` (should already exist)

If files are missing, they need to be added to the repository first.

## Step 6: Test the Workflow

1. **Manually Trigger**:
   - Go to: `https://github.com/YOUR_USERNAME/YOUR_REPO/actions`
   - Find **"Weekly Stale PR Notifications"**
   - Click **"Run workflow"** dropdown → **"Run workflow"**
   - Click the green **"Run workflow"** button

2. **Check Results**:
   - Wait for the workflow to complete (usually 10-30 seconds)
   - Review the workflow logs for any errors
   - Check your Slack channel for the notification
   - You should see either:
     - A list of stale PRs (if any exist)
     - A "No stale PRs found" message (if none are stale)

## Step 7: Verify Weekly Schedule

The workflow is configured to run automatically every Monday at 9 AM UTC.

**To verify or change the schedule**:

1. Edit `.github/workflows/stale-pr-notifications.yml`
2. Find the `cron` line:
   ```yaml
   - cron: '0 9 * * 1'  # Every Monday at 9 AM UTC
   ```
3. Adjust as needed using [crontab.guru](https://crontab.guru/)

**Common schedules**:
- `'0 9 * * 1'` - Every Monday at 9 AM UTC
- `'0 14 * * 1'` - Every Monday at 2 PM UTC (9 AM EST)
- `'0 9 * * 1,4'` - Every Monday and Thursday at 9 AM UTC

## How It Works

1. **Runs on schedule** (every Monday at 9 AM UTC) or manually
2. **Fetches all open PRs** from the repository
3. **Identifies stale PRs** (haven't been updated in X hours/days)
4. **Detects CODEOWNERS** for each stale PR based on changed files
5. **Posts to Slack channel** with:
   - PR details (number, title, author, time stale)
   - Requested reviewers
   - CODEOWNERS (tagged as Slack groups)

## Message Format

Each Slack notification includes:

- **Header**: Number of stale PRs found
- **Summary**: Total count and staleness threshold
- **For each stale PR**:
  - PR number and title (clickable link)
  - Author
  - Time stale (formatted as hours or days+hours, e.g., "2h" or "1d 3h")
  - Requested reviewers (tagged for notification)
  - CODEOWNERS (tagged as Slack user groups/users based on changed files)

## Troubleshooting

### Workflow Not Running

**Symptoms**: Workflow doesn't appear in Actions tab or doesn't run on schedule

**Solutions**:
- Verify workflow file exists: `.github/workflows/stale-pr-notifications.yml`
- Check Actions are enabled: Go to Settings → Actions → General → Ensure "Allow all actions" is selected
- Verify cron syntax: Use [crontab.guru](https://crontab.guru/) to validate schedule
- Check workflow file syntax: Ensure YAML is valid (no indentation errors)

### No Slack Notifications

**Symptoms**: Workflow runs successfully but no message appears in Slack

**Solutions**:
- **Verify webhook URL**: Check that `SLACK_WEBHOOK_URL` secret is set correctly
- **Test webhook manually**: Use curl to test:
  ```bash
  curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"Test message"}' \
    YOUR_WEBHOOK_URL
  ```
- **Check workflow logs**: Go to Actions → Select the workflow run → Check for errors
- **Verify channel**: Ensure the webhook is configured for the correct Slack channel
- **Check Slack app permissions**: Ensure the app has permission to post to the channel

### PRs Not Detected as Stale

**Symptoms**: PRs that should be stale aren't being reported

**Solutions**:
- **Verify threshold**: Check that `STALE_HOURS` or `STALE_DAYS` is set correctly
- **Check PR update time**: The script uses `updated_at` field from GitHub API
- **Review script logs**: Check workflow logs to see which PRs were checked and their timestamps
- **Test with shorter threshold**: Temporarily set `STALE_HOURS=1` to test

### CODEOWNERS Not Detected

**Symptoms**: CODEOWNERS are not shown in notifications

**Solutions**:
- **Verify CODEOWNERS file**: Ensure `.github/CODEOWNERS` exists and is properly formatted
- **Check file matching**: The script uses pattern matching; verify your CODEOWNERS patterns match changed files
- **Review script logs**: Check workflow logs to see which CODEOWNERS rules were matched

### Teams Not Tagged in Slack

**Symptoms**: CODEOWNERS are detected but not tagged as Slack groups

**Solutions**:
- **Verify mapping file**: Ensure `.github/scripts/slack_team_mapping.json` exists and contains correct mappings
- **Check Slack group IDs**: Verify the IDs in your mapping file are correct (they start with `S`)
- **Test group mentions**: Try manually mentioning the group in Slack to verify the ID format
- **Review script logs**: Check workflow logs to see which CODEOWNERS were detected

### Workflow Fails with Permission Errors

**Symptoms**: Workflow fails with "Permission denied" or "403" errors

**Solutions**:
- **Check repository permissions**: Ensure GitHub Actions is enabled
- **Verify GITHUB_TOKEN**: This is automatically provided, but check workflow permissions
- **Review workflow permissions**: Ensure workflows have `contents: read` and `pull-requests: read` permissions

## Configuration Reference

### Required Secrets

| Secret Name | Description | Example |
|------------|-------------|---------|
| `SLACK_WEBHOOK_URL` | Webhook URL for Slack channel | `https://hooks.slack.com/services/YOUR_WEBHOOK_URL` |

### Optional Variables

| Variable Name | Description | Default | Example |
|--------------|-------------|---------|---------|
| `STALE_HOURS` | Hours before PR is considered stale | Uses `STALE_DAYS` | `24` (1 day) |
| `STALE_DAYS` | Days before PR is considered stale (fallback) | `3` | `3` (3 days = 72 hours) |
| `SLACK_CHANNEL` | Channel name (for reference) | N/A | `#engineering` |

### Optional Secrets

| Secret Name | Description | Format |
|------------|-------------|--------|
| `SLACK_TEAM_MAPPING` | GitHub to Slack team mapping | JSON string: `{"Back-End": "S12345678"}` |

## File Structure

```
your-repo/
├── .github/
│   ├── workflows/
│   │   └── stale-pr-notifications.yml  # Main workflow
│   ├── scripts/
│   │   ├── check_stale_prs.py          # Main script
│   │   └── slack_team_mapping.json     # Team mapping (optional)
│   └── CODEOWNERS                      # File ownership rules
```

## Security Considerations

- **Webhook URLs are secrets**: Never commit webhook URLs to the repository
- **GitHub Token**: Workflows use `GITHUB_TOKEN` which is automatically provided by GitHub Actions
- **Permissions**: Workflows only need `read` permissions for contents and pull-requests
- **Slack Tokens**: Webhook URLs provide limited access - they can only post to the configured channel
- **Team Mapping**: If stored in repository, ensure it doesn't contain sensitive information

## Maintenance

### Regular Tasks

- **Monitor workflow runs**: Check Actions tab weekly to ensure workflows are running
- **Review notifications**: Verify notifications are accurate and helpful
- **Update team mappings**: If Slack group IDs change, update the mapping file
- **Adjust thresholds**: Modify `STALE_HOURS` if needed based on team feedback

### Updates

- **Workflow files**: Can be updated by editing `.github/workflows/stale-pr-notifications.yml`
- **Script logic**: Can be updated by editing `.github/scripts/check_stale_prs.py`
- **After updates**: Test workflows manually before relying on scheduled runs

## Support and Resources

- **GitHub Actions Documentation**: https://docs.github.com/en/actions
- **Slack Incoming Webhooks**: https://api.slack.com/messaging/webhooks
- **GitHub API - Pull Requests**: https://docs.github.com/en/rest/pulls/pulls
- **GitHub CODEOWNERS Documentation**: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- **Cron Schedule Helper**: https://crontab.guru/

## Quick Setup Checklist

- [ ] Create Slack webhook
- [ ] Add `SLACK_WEBHOOK_URL` secret to GitHub
- [ ] Set `STALE_HOURS` variable (optional, for faster testing)
- [ ] Find Slack user group IDs (optional)
- [ ] Create `slack_team_mapping.json` file (optional)
- [ ] Test workflow manually
- [ ] Verify workflow runs on schedule
- [ ] Monitor first few scheduled runs

## Estimated Setup Time

- **Initial Setup**: 10-15 minutes
- **Testing**: 5-10 minutes
- **Total**: ~15-25 minutes

---

**Questions?**: Refer to the troubleshooting section above or contact the engineering team.
