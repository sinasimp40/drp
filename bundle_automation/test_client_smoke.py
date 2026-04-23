"""Smoke test: hit a running license server (port 5050) with the client
script's own functions to prove the multipart upload + status query work
end-to-end over real HTTP. Skip the install/uninstall steps because they
need Windows."""
import io
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_and_upload as b


def run():
    print(f"LICENSE_SERVER_URL={b.LICENSE_SERVER_URL}")
    assert b.LICENSE_SERVER_URL, "set LICENSE_SERVER_URL"
    assert b.BUNDLE_AUTOMATION_TOKEN, "set BUNDLE_AUTOMATION_TOKEN"
    b._log_setup()

    status = b.server_get_status()
    print(f"status: {status}")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("RobloxPlayerBeta.exe", b"FAKE PLAYER" * 100)
        zf.writestr("content/x.dat", b"data")
    tmpzip = tempfile.NamedTemporaryFile(suffix=".zip", delete=False).name
    open(tmpzip, "wb").write(buf.getvalue())

    nv = status["next_version"]
    result = b.server_upload_bundle(tmpzip, version=nv, note="version-CLIENTTEST")
    print(f"upload: {result}")
    assert result["ok"], result
    assert result["version"] == nv

    status2 = b.server_get_status()
    assert status2["current"]["note"] == "version-CLIENTTEST"
    assert status2["current"]["version"] == nv
    print(f"status after upload: {status2}")
    print("CLIENT-SCRIPT SMOKE TEST PASSED")
    os.remove(tmpzip)


if __name__ == "__main__":
    run()
