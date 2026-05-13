from unittest.mock import patch

import pytest

from src.email_service import send_evaluation_email
from src.shared.models import IssueEvaluation
from src.email_service import score_badge


@pytest.mark.asyncio
async def test_send_evaluation_email_skips_below_threshold(sample_repo, sample_issue):
    ev = IssueEvaluation(
        score=10,
        difficulty="Low",
        scope="Small",
        impression="Not worth it.",
        reasoning="Score too low.",
    )

    with patch("src.email_service._send_smtp") as mock_smtp:
        await send_evaluation_email(sample_repo, sample_issue, ev)
        mock_smtp.assert_not_called()


@pytest.mark.asyncio
async def test_send_evaluation_email_sends_above_threshold(sample_repo, sample_issue):
    ev = IssueEvaluation(
        score=75,
        difficulty="Medium",
        scope="Small",
        impression="Worth it.",
        reasoning="Good issue.",
    )

    with patch("src.email_service._send_smtp") as mock_smtp:
        with patch("src.email_service.settings") as mock_settings:
            mock_settings.MIN_SCORE_TO_NOTIFY = 40
            mock_settings.EMAIL_FROM = "test@test.com"
            mock_settings.EMAIL_TO = "to@test.com"
            mock_settings.GMAIL_APP_PASSWORD = "password"

            await send_evaluation_email(sample_repo, sample_issue, ev)
            mock_smtp.assert_called_once()


def test_high_priority():
    assert score_badge(80) == "🟢 High Priority"
    assert score_badge(100) == "🟢 High Priority"


def test_worth_exploring():
    assert score_badge(60) == "🟡 Worth Exploring"
    assert score_badge(79) == "🟡 Worth Exploring"


def test_low_priority():
    assert score_badge(40) == "🟠 Low Priority"
    assert score_badge(59) == "🟠 Low Priority"


def test_skip():
    assert score_badge(0) == "🔴 Skip"
    assert score_badge(39) == "🔴 Skip"
