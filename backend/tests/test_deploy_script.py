import os

DEPLOY_SH = os.path.join(
    os.path.dirname(__file__), "..", "..", "deploy", "deploy.sh"
)


def test_deploy_migrates_after_install_and_before_restarting_services():
    with open(DEPLOY_SH) as f:
        script = f.read()

    install = script.index("pip install")
    migrate = script.index("backend/migrate.py")
    restart = script.index("systemctl restart")

    assert install < migrate < restart
