import click

from track_github_issues.tracker import GitHubIssueTracker


def parse_comma_list(ctx, param, value):
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def run_tracker(users, orgs, per_page, page_limit, gh_token):
    """
    Core logic to track issues.
    """
    print(f'Tracking issues for users: {users}')
    print(f'Filtering by organizations: {orgs}')
    print(f'Settings: per_page={per_page}, page_limit={page_limit}')

    if not gh_token:
        click.echo('Error: No GitHub token provided.', err=True)
        return

    tracker = GitHubIssueTracker(
        users=users,
        orgs=orgs,
        per_page=per_page,
        page_limit=page_limit,
        gh_token=gh_token,
    )
    tracker.run()


@click.command()
@click.option(
    '--users',
    required=True,
    callback=parse_comma_list,
    help='Comma-separated list of GitHub usernames',
)
@click.option(
    '--orgs',
    default='',
    callback=parse_comma_list,
    help='Comma-separated list of organizations',
)
@click.option('--per-page', default=100, type=int, help='Results per page')
@click.option('--page-limit', default=10, type=int, help='Number of pages to fetch')
@click.option('--gh-token', envvar='GH_TOKEN', help='GitHub API Token')
def main(users, orgs, per_page, page_limit, gh_token):
    """Track assigned GitHub issues."""
    run_tracker(
        users=users,
        orgs=orgs,
        per_page=per_page,
        page_limit=page_limit,
        gh_token=gh_token,
    )
