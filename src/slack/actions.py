from slack_bolt import Ack, Say


def register_actions(app, draft_approval_handler):
    @app.action("approve_draft")
    def handle_approve_draft(ack: Ack, body: dict, say: Say):
        draft_approval_handler.handle_approval_action(ack, body, say)

    @app.action("reject_draft")
    def handle_reject_draft(ack: Ack, body: dict, say: Say):
        draft_approval_handler.handle_approval_action(ack, body, say)

    @app.action("edit_draft")
    def handle_edit_draft(ack: Ack, body: dict, say: Say):
        draft_approval_handler.handle_approval_action(ack, body, say)

    @app.action("save_draft")
    def handle_save_draft(ack: Ack, body: dict, say: Say):
        draft_approval_handler.handle_approval_action(ack, body, say)
