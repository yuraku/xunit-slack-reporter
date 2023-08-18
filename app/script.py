import os
import pathlib
import sys
import time

from app import constants
from app.utils import slack_utils
from app.utils import xunit_utils


def main():
    # Check input values.
    if constants.XUNIT_PATH_ENV_VAR not in os.environ and constants.XUNIT_PATH_GLOB_ENV_VAR not in os.environ:
        raise Exception(
            f"xunit file(s) not found!  Please make sure to set the {constants.XUNIT_PATH_ENV_VAR} or {constants.XUNIT_PATH_GLOB_ENV_VAR} env variable!")

    if constants.SLACK_CHANNEL_ENV_VAR not in os.environ:
        raise Exception(f"Slack channel!  Please make sure to set the {constants.SLACK_CHANNEL_ENV_VAR} env variable!")

    if constants.SLACK_TOKEN_ENV_VAR not in os.environ:
        raise Exception(f"Slack channel!  Please make sure to set the {constants.SLACK_TOKEN_ENV_VAR} env variable!")

    # Load configs
    only_notify_on_issues = os.getenv(constants.ONLY_NOTIFY_ON_ISSUES_ENV_VAR, "false").lower() == 'true'
    exit_on_failure = os.getenv(constants.EXIT_ON_FAILURE_ENV_VAR, "false").lower() == 'true'

    # Load XUnit report(s)
    xunit_path = os.getenv(constants.XUNIT_PATH_ENV_VAR, "")
    xunit_glob = os.getenv(constants.XUNIT_PATH_GLOB_ENV_VAR, "")

    if xunit_glob:
        working_dir = pathlib.Path(os.getenv('GITHUB_WORKSPACE'))
        files = working_dir.glob(xunit_glob)
    elif xunit_path:
        files = [pathlib.Path(xunit_path)]

    # Report on files
    failed_tests = False

    number_of_passed_tests = 0
    number_of_failed_tests = 0
    number_of_broken_tests = 0
    number_of_tests = 0
    time_elapsed = 0.0
    file_contains_failures = False

    for file in files:
        xunit_report = xunit_utils.read_xunit(file)
        if bool(xunit_report.errors or xunit_report.failures):
            file_contains_failures = bool(xunit_report.errors or xunit_report.failures)

        number_of_passed_tests = number_of_passed_tests + xunit_report.tests - xunit_report.errors - xunit_report.failures
        number_of_failed_tests = number_of_failed_tests + xunit_report.failures
        number_of_broken_tests = number_of_broken_tests + xunit_report.errors
        number_of_tests = number_of_tests + xunit_report.tests
        time_elapsed = time_elapsed + xunit_report.time

    # Slack results
    author_name = "JUnit Slack Reporter" if constants.SLACK_MESSAGE_TITLE_ENV_VAR not in os.environ else os.getenv(
        constants.SLACK_MESSAGE_TITLE_ENV_VAR, "")

    slack_attachment = {
        "color": constants.PASS_COLOR,
        "author_name": author_name,
        "author_link": f"https://github.com/{os.getenv('GITHUB_REPOSITORY')}/actions/runs/{os.getenv('GITHUB_RUN_ID')}",
        "title": f"Test results for \"{os.getenv('GITHUB_WORKFLOW')}\" on \"{os.getenv('GITHUB_REF')}\"",
        "fields": []
    }

    slack_attachment['fields'].append({
        "title": "Total # of tests",
        "value": f"{number_of_tests}",
        "short": True
    })

    slack_attachment['fields'].append({
        "title": "Tests passed",
        "value": f"{number_of_passed_tests}",
        "short": True
    })

    slack_attachment['fields'].append({
        "title": "Tests errored",
        "value": f"{number_of_broken_tests}",
        "short": True
    })

    slack_attachment['fields'].append({
        "title": "Tests failed",
        "value": f"{number_of_failed_tests}",
        "short": True
    })

    slack_attachment['fields'].append({
        "title": "Time elapsed",
        "value": time.strftime("%H:%M:%S", time.gmtime(round(time_elapsed))),
        "short": True
    })

    if file_contains_failures:
        slack_attachment['color'] = constants.FAIL_COLOR

        # If success, only send if configured.
        if not file_contains_failures:
            if not only_notify_on_issues:
                slack_utils.send_slack_msg(
                    os.getenv(constants.SLACK_CHANNEL_ENV_VAR),
                    attachments=[slack_attachment]
                )
            # If error or failure.
        else:
            slack_utils.send_slack_msg(
                os.getenv(constants.SLACK_CHANNEL_ENV_VAR),
                attachments=[slack_attachment]
            )
            failed_tests = True

    # Return appropriate status code.
    if exit_on_failure:
        if failed_tests:
            sys.exit(1)


if __name__ == "__main__":
    main()
