from tinydb import TinyDB, Query
from flask import Flask, request
import os
import hashlib
from cryptography.fernet import Fernet
import base64

app = Flask(__name__)
db = TinyDB("db.json")
password = hashlib.sha1(os.getenv("TDBW_PASSWORD").encode("utf-8")).hexdigest()
bpassword = base64.urlsafe_b64encode((password[:31]+"=").encode("utf-8"))
enc = Fernet(bpassword)


def handle_req():
    json = request.get_json()
    if json is None:
        return {}
    if json.get("password") is not None:
        given_pw = json["password"]
    else:
        return {}
    if given_pw != password:
        return {}

    json["params"] = eval(enc.decrypt(json["params"].encode("utf-8")))

    if json["method"] == "search":
        return {"result": db.search(Query().fragment(json["params"])), "success": True}
    elif json["method"] == "insert":
        db.insert(json["params"])
        return {"success": True, "result": None}

    return {"success": False}


@app.route("/")
def main():
    res = handle_req()
    if res.get("success"):
        return {"result": enc.encrypt(str(res["result"]).encode("utf-8")), "success": True}
    else:
        return res


if __name__ == "__main__":
    app.run("0.0.0.0", int(os.environ.get("PORT", 5000)))
