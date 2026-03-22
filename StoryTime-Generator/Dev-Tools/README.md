# Dev-Tools - Utility Scripts

Quick utility scripts for development and monitoring of the StoryTime Generator.

## check_api_limits.py

A lightweight script to check your GitHub Models API quotas and rate limit status before running generation tasks.

### Usage

```bash
python Dev-Tools/check_api_limits.py
```

### What It Checks

✅ **GitHub Token Status** - Verifies `.env` configuration
✅ **GitHub API Rate Limits** - Checks REST API rate limiting
✅ **Models API Availability** - Confirms API server is responding
✅ **Request Quotas** - Shows remaining requests and usage percentage
✅ **Status Warnings** - Alerts if limits are running low

### Output Example

```
============================================================
GitHub Models API Rate Limit Status
Checked: 2026-03-22 14:30:45
============================================================

GitHub REST API Rate Limits:
  • Limit:     5000 requests/hour
  • Remaining: 4850
  • Status:    ✅ GOOD (97.0% remaining)

GitHub Models API Status:
  • API is available
  • Limit:     1000 requests
  • Remaining: 987 requests
  • Status:    ✅ GOOD (98.7% remaining)

============================================================
Tips for Managing API Quotas:
  1. Check limits regularly before heavy workloads
  2. Use lower cost models (gpt-4o-mini) when possible
  3. Batch requests together when feasible
  4. Implement exponential backoff for retries
  5. Monitor costs in GitHub Settings
============================================================
```

### Status Indicators

| Status | Color | Meaning |
|--------|-------|---------|
| ✅ GOOD | Green | 75%+ remaining - safe to use |
| ℹ️ MODERATE | Blue | 50-75% remaining - monitor usage |
| ⚠️ LOW | Yellow | 25-50% remaining - be cautious |
| 🚨 CRITICAL | Red | <25% remaining - wait before using |

### Setup Requirements

1. Ensure `.env` file has `GITHUB_TOKEN`:
   ```
   GITHUB_TOKEN=your_token_here
   ```

2. Install required dependencies:
   ```bash
   pip install requests python-dotenv
   ```

### Tips for Avoiding Rate Limits

1. **Check Often** - Run this script before starting major generation tasks
2. **Use Efficient Models** - `gpt-4o-mini` has better rates than `gpt-4o`
3. **Batch Requests** - Group multiple operations when possible
4. **Implement Backoff** - Add delays between requests if approaching limits
5. **Cache Results** - Save generated stories to avoid regenerating
6. **Monitor Billing** - Check [GitHub Settings](https://github.com/settings) for usage details

### Automation Tip

Add to your workflow before running generation:

```bash
# Check limits first
python Dev-Tools/check_api_limits.py

# If limits are good, run the story generator
python app.py
```

### Troubleshooting

**Error: GITHUB_TOKEN not found**
- Create/update `.env` file in the StoryTime-Generator directory
- Add: `GITHUB_TOKEN=your_github_token_here`
- Get token: https://github.com/settings/personal-access-tokens

**Error: Connection timeout**
- Check internet connection
- GitHub Models API might be temporarily unavailable
- Try again in a few moments

**Error: 401 Unauthorized**
- Your token is invalid or expired
- Generate a new token at: https://github.com/settings/personal-access-tokens
- Update `.env` with new token

### Future Tools

This directory is for development utilities. Consider adding:
- `generate_sample_stories.py` - Batch story generation for testing
- `api_cost_calculator.py` - Estimate costs for story generation
- `token_validator.py` - Validate API token before running main app
- `batch_processor.py` - Process multiple stories in parallel
