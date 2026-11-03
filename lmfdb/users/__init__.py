"""
The LMFDB's user accounts are lmfdb-utils' (lmfdb_utils.users, set up by
lmfdb_utils.web.init_app in lmfdb/app.py); this adds the pages only the LMFDB
has: reviewing data uploads, and restarting the servers.
"""

from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from lmfdb_utils.users.main import (
    login_page,
    login_manager,
    admin_required,
    knowl_reviewer_required,
    housekeeping,
)
from lmfdb_utils.utilities import to_dict
from lmfdb.app import app
from lmfdb.utils.uploader import Uploader

assert login_page  # silence pyflakes
assert login_manager  # silence pyflakes
assert knowl_reviewer_required  # silence pyflakes
assert housekeeping  # silence pyflakes

lmfdb_users_page = Blueprint("lmfdb_users", __name__, template_folder="templates")


@lmfdb_users_page.context_processor
def body_class():
    return {'body_class': 'login'}


class Reviewer(Uploader):
    """
    This uploader is used to collect UploadSection objects from different sections of the LMFDB that use them.
    """
    def __init__(self):
        from lmfdb.modular_curves.upload import Points, PointCompleteness, GonalityBounds, Models, UniversalEC, MultiKnowl
        super().__init__([Points(), PointCompleteness(), GonalityBounds(), Models(), UniversalEC(), MultiKnowl()])


@lmfdb_users_page.route("/uploads", methods=["GET", "POST"])
@login_required
def review_uploads():
    uploader = Reviewer()
    reviewer = current_user.is_knowl_reviewer()
    if request.method == "POST":
        info = to_dict(request.form)
        uploader.review(info, reviewer, current_user.id)
    else:
        info = to_dict(request.args)

    user_shown = info.get("user_shown", "" if reviewer else current_user.id)
    reviewing = (reviewer and not user_shown)
    results, statuses = uploader.show_uploads(info, reviewing, user_shown)

    return render_template(
        "user-uploads.html",
        title="Review data uploads",
        uploader=uploader,
        statuses=statuses,
        results=results,
        user_shown=user_shown,
    )


@app.route("/restartserver")
@admin_required
def restart():
    from subprocess import Popen, PIPE
    from urllib.parse import urlparse
    urlparts = urlparse(request.url)
    if urlparts.netloc == "beta.lmfdb.org":
        command = ['bash', '/home/lmfdb/restart-dev']
    elif urlparts.netloc in ["prodweb1.lmfdb.xyz", "prodweb2.lmfdb.xyz"]:
        command = ['bash', '/home/lmfdb/restart-web']
    else:
        command = None
    if command:
        out = Popen(command, stdout=PIPE, encoding='utf-8').communicate()[0]
        return out.replace('\n', '<br>')
    else:
        return "Only supported in beta.lmfdb.org, prodweb1.lmfdb.xyz, and prodweb2.lmfdb.xyz"


app.register_blueprint(lmfdb_users_page, url_prefix="/users")
