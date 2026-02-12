import logging

from src.slack_handlers.draft_approval_handler import DraftApprovalHandler


def test_draft_approval_handler_logging(caplog, mocker):
    """Test logging in draft approval handler"""

    slack_app = mocker.Mock()
    gmail_writer = mocker.Mock()
    say_mock = mocker.Mock()

    draft_handler = DraftApprovalHandler(gmail_writer=gmail_writer, slack_app=slack_app)

    draft_handler.pending_drafts["test_draft_id"] = {
        "draft": {"id": "draft_123"},
        "decoded_draft": {},
        "user_id": "test_user_id",
        "status": "pending",
        "slack_message_ts": "1234567890.123456",
        "slack_channel": "C12345",
    }
    with caplog.at_level(logging.INFO):
        draft_handler._handle_approve("test_draft_id", "test_user_id", say_mock)
        draft_handler._handle_reject("test_draft_id", "test_user_id", say_mock)
        draft_handler._handle_save("test_draft_id", "test_user_id", say_mock)

    assert "Draft approved - draft_id=test_draft_id user_id=test_user_id" in caplog.text
    assert "Draft rejected - draft_id=test_draft_id user_id=test_user_id" in caplog.text
    assert "Draft saved - draft_id=test_draft_id user_id=test_user_id" in caplog.text
