
# Track GitHub Issues Assigned to You

An action to track all GitHub issues assigned to you across multiple organizations
by creating tracking issues in the current repository.

Once the open issues are aggregated, you can use GitHub Projects to manage and
track your work across different repositories and organizations.

## Key Features

- **Automatic Aggregation**: Automatically fetches all issues assigned to you across
  all organizations.
- **Auto-Close**: Tracking issues are automatically closed when the original issue is
  closed.
- **Clear Links**: Each tracking issue contains a direct link to the original issue.

## How to Use

We recommend creating a dedicated repository for tracking your issues. The action is
designed to be run as a scheduled GitHub Actions workflow in your repository.

The action can be added to your workflow as follows:

```yaml
name: Track Issues

on:
  schedule:
    - cron: '0 * * * *'   # Set how often to check for issue updates. For example, run every hour.
  workflow_dispatch:      # Allow manual triggering

permissions:
  issues: write
  contents: read

jobs:
  track-issues:
    runs-on: ubuntu-latest
    steps:
      - name: Run track-github-issues Action
        uses: ka-sarthak/track-github-issues@v1.0.1
        with:
          users: "user1,user2" 
          organizations: "org1,org2"
          
          # Optional configuration parameters for pagination
          per_page: 100 
          page_limit: 10
```

## Configuration Options

- `users`: Comma-separated list of GitHub usernames whose assigned issues
  should be tracked.
- `organizations`: (Optional) Comma-separated list of organization names to filter
  issues from. If not specified, issues from all accessible organizations (based on the
  token's permissions) will be tracked.
- `per_page`: (Optional) Number of results per page for API requests. Default: 100
- `page_limit`: (Optional) Maximum number of pages to fetch. Default: 10

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for
details.
