"""Module for tracking GitHub issues across organizations."""

import os
import re
import sys

import requests


class GitHubIssueTracker:
    """Main class for tracking issues across organizations."""

    def __init__(
        self,
        users: list[str],
        orgs: list[str],
        per_page: int,
        page_limit: int,
        gh_token: str,
    ):
        """Initialize the issue tracker with configuration."""

        self.users = users
        self.organizations = orgs
        self.per_page = per_page
        self.page_limit = page_limit
        self.headers = {
            'Authorization': f'Bearer {gh_token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        }

        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Get repository information from environment or API
        self.repo_owner, self.repo_name = self._get_repo_info()
        print(f'Repository: {self.repo_owner}/{self.repo_name}')

    def _get_repo_info(self) -> tuple[str, str]:
        """Get repository owner and name from environment or GitHub API."""
        # Try to get from GITHUB_REPOSITORY env var first (available in GitHub Actions)
        github_repo = os.environ.get('GITHUB_REPOSITORY')
        if github_repo and '/' in github_repo:
            owner, name = github_repo.split('/', 1)
            return owner, name

        # Fallback: get from git remote
        try:
            import subprocess

            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                capture_output=True,
                text=True,
                check=True,
            )
            remote_url = result.stdout.strip()
            # Parse GitHub URL (https or ssh)
            match = re.search(r'github\.com[:/]([^/]+)/([^/.]+)', remote_url)
            if match:
                return match.group(1), match.group(2)
        except Exception as e:
            print(f'Error getting repo info from git: {e}')

        print('Error: Could not determine repository information')
        sys.exit(1)

    def _get_repo_name_from_url(self, repo_url: str) -> str:
        """Extract repository name from API URL."""
        # Format: https://api.github.com/repos/owner/repo
        match = re.search(r'/repos/([^/]+/[^/]+)', repo_url)
        return match.group(1) if match else repo_url

    def _extract_original_issue_url(self, body: str | None) -> str | None:
        """Extract original issue URL from tracking issue body."""
        if not body:
            return None
        match = re.search(
            r'\*\*Original Issue:\*\* (https://github\.com/[^\s)]+)', body
        )
        return match.group(1) if match else None

    def _parse_issue_url(self, url: str) -> dict[str, str] | None:
        """Parse GitHub issue URL into components."""
        match = re.search(r'github\.com/([^/]+)/([^/]+)/issues/(\d+)', url)
        if match:
            return {
                'owner': match.group(1),
                'repo': match.group(2),
                'issue_number': match.group(3),
            }
        return None

    def _is_original_issue_closed(self, issue_url: str) -> bool:
        """Check if the original issue is closed."""
        parsed = self._parse_issue_url(issue_url)
        if not parsed:
            return False

        try:
            response = self.session.get(
                f'https://api.github.com/repos/{parsed["owner"]}/'
                f'{parsed["repo"]}/issues/{parsed["issue_number"]}'
            )
            if response.status_code == 200:
                issue = response.json()
                return issue.get('state') == 'closed'
        except Exception as e:
            print(f'Error checking issue {issue_url}: {e}')

        return False

    def get_assigned_issues(self) -> list[dict]:
        """Get all issues assigned to configured users."""
        all_issues = []

        for username in self.users:
            print(f'Fetching issues for user: {username}')

            # Build search query
            query_parts = ['is:issue', 'is:open', f'assignee:{username}']

            # Add organization filter if specified
            if self.organizations:
                org_filter = ' '.join([f'org:{org}' for org in self.organizations])
                query_parts.append(f'{org_filter}')

            search_query = ' '.join(query_parts)

            # Calculate effective limit
            effective_limit = min(self.per_page * self.page_limit, 1000)

            # Search issues
            try:
                response = self.session.get(
                    'https://api.github.com/search/issues',
                    params={
                        'q': search_query,
                        'per_page': effective_limit,
                        'sort': 'updated',
                        'order': 'desc',
                    },
                )
                if response.status_code == 200:
                    data = response.json()
                    all_issues.extend(data.get('items', []))
                else:
                    print(f'Error searching issues: {response.status_code}')
            except Exception as e:
                print(f'Error fetching assigned issues: {e}')

        # Remove duplicates by issue ID
        unique_issues = {issue['id']: issue for issue in all_issues}.values()

        # Filter out issues from the current repository
        current_repo_url = (
            f'https://api.github.com/repos/{self.repo_owner}/{self.repo_name}'
        )
        filtered_issues = [
            issue
            for issue in unique_issues
            if issue.get('repository_url') != current_repo_url
        ]

        return filtered_issues

    def get_existing_tracking_issues(self) -> list[dict]:
        """Get existing tracking issues in the current repo."""
        all_issues = []
        page = 1

        # Calculate effective limit
        effective_limit = min(self.per_page * self.page_limit, 1000)

        while page <= self.page_limit:
            try:
                response = self.session.get(
                    f'https://api.github.com/repos/{self.repo_owner}/'
                    f'{self.repo_name}/issues',
                    params={
                        'state': 'all',
                        'labels': 'tracked-issue',
                        'per_page': min(self.per_page, 100),
                        'page': page,
                    },
                )
                if response.status_code == 200:
                    issues = response.json()
                    if not issues:
                        break
                    all_issues.extend(issues)
                    if len(issues) < self.per_page:
                        break
                    page += 1
                else:
                    print(f'Error fetching tracking issues: {response.status_code}')
                    break
            except Exception as e:
                print(f'Error fetching existing tracking issues: {e}')
                break

        return all_issues

    def create_tracking_issue(self, issue: dict) -> int | None:
        """Create a new tracking issue."""
        original_url = issue['html_url']
        title = issue['title']
        body = issue.get('body') or 'No description provided.'
        state = issue['state']
        created_at = issue['created_at']
        updated_at = issue['updated_at']
        repo_url = issue['repository_url']
        repo_name = self._get_repo_name_from_url(repo_url)

        issue_body = f"""**Original Issue:** {original_url}

**Repository:** {repo_name}
**State:** {state}
**Created:** {created_at}
**Updated:** {updated_at}

---

{body}"""

        try:
            response = self.session.post(
                f'https://api.github.com/repos/{self.repo_owner}'
                f'/{self.repo_name}/issues',
                json={
                    'title': f'[{repo_name}] {title}',
                    'body': issue_body,
                    'labels': ['tracked-issue'],
                },
            )
            if response.status_code == 201:
                new_issue = response.json()
                return new_issue['number']
            else:
                print(
                    f'Error creating tracking issue for {original_url}: '
                    f'{response.status_code}'
                )
        except Exception as e:
            print(f'Error creating tracking issue for {original_url}: {e}')

        return None

    def close_tracking_issue(self, issue_number: int):
        """Close a tracking issue."""
        try:
            # Close the issue
            response = self.session.patch(
                f'https://api.github.com/repos/{self.repo_owner}'
                f'/{self.repo_name}/issues/{issue_number}',
                json={'state': 'closed'},
            )
            if response.status_code == 200:
                # Add a comment
                self.session.post(
                    f'https://api.github.com/repos/{self.repo_owner}'
                    f'/{self.repo_name}/issues/{issue_number}/comments',
                    json={
                        'body': (
                            'Closing this tracking issue as the original '
                            'issue has been closed.'
                        )
                    },
                )
            else:
                print(
                    f'Error closing tracking issue #{issue_number}: '
                    f'{response.status_code}'
                )
        except Exception as e:
            print(f'Error closing tracking issue #{issue_number}: {e}')

    def run(self):
        """Main execution method."""
        print('Starting issue sync...')

        # Get all assigned issues
        assigned_issues = self.get_assigned_issues()
        print(f'Found {len(assigned_issues)} assigned issues across organizations')

        # Get existing tracking issues
        tracking_issues = self.get_existing_tracking_issues()
        print(f'Found {len(tracking_issues)} existing tracking issues in this repo')

        # Track processed URLs
        processed_urls: set[str] = set()

        # Process assigned issues: create tracking issues as needed
        for issue in assigned_issues:
            original_url = issue['html_url']
            processed_urls.add(original_url)

            # Check if tracking issue exists
            existing_tracking = None
            for tracking in tracking_issues:
                tracking_body = tracking.get('body', '')
                if original_url in tracking_body:
                    existing_tracking = tracking
                    break

            if not existing_tracking:
                # Create new tracking issue
                print(f'Creating tracking issue for: {original_url}')
                issue_number = self.create_tracking_issue(issue)
                if issue_number:
                    print(f'Created tracking issue #{issue_number}')
            else:
                print(
                    f'Tracking issue exists for: {original_url} '
                    f'(issue #{existing_tracking["number"]})'
                )

        # Close tracking issues for which the original issue is closed or no
        # longer assigned
        print('Checking for tracking issues to close...')
        for tracking in tracking_issues:
            if tracking['state'] != 'open':
                continue

            original_url = self._extract_original_issue_url(tracking.get('body'))
            if not original_url:
                continue

            # Check if this issue was in our processed list
            if original_url in processed_urls:
                # Issue is still assigned, keep it open
                continue

            # Check if original issue is closed
            if self._is_original_issue_closed(original_url):
                print(
                    f'Closing tracking issue #{tracking["number"]} - original issue '
                    'is closed'
                )
                self.close_tracking_issue(tracking['number'])

        print('Issue sync completed!')
