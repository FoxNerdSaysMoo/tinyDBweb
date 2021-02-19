from tinydb import TinyDB, Query
from sanic import Sanic, request, response
import os
import hashlib
from cryptography.fernet import Fernet
import base64
import atexit

app = Sanic(__name__)

db = TinyDB("db.json")
atexit.register(db.close)

password = hashlib.sha1(os.getenv("TDBW_PASSWORD").encode("utf-8")).hexdigest()
bpassword = base64.urlsafe_b64encode(os.getenv("TDBW_PASSWORD")[:32].encode("utf-8"))
enc = Fernet(bpassword)


def handle_req(request: request):
    json = request.json
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

    elif json["method"] == "op-search":
        def opsearch(q):
            res = True
            for item, op, const in json["params"]:
                if not eval(f"q[{repr(item)}] {op} {repr(const)}"):
                    return False
            return res
        return {"success": True, "result": list(filter(opsearch, db.all()))}

    elif json["method"] == "find-search":
        def find(val):
            return str(val).lower().find(json["params"]["find"].lower()) >= 0
        return {
            "success": True,
            "result": [x for x in filter(find, db.search(Query().fragment(json["params"]["frag"])))]
        }

    elif json["method"] == "top-search":
        greatest = []
        valids = db.search(Query().fragment(json["params"]["frag"]))
        measurement = json["params"]["greatest"]
        max = json["params"]["max"]

        def min():
            minimum = None
            for item in greatest:
                if minimum == None:
                    minimum = item
                elif item[measurement] < minimum:
                    minimum = item
            return minimum

        for item in valids:
            minimum = min()
            if (item[measurement] > minimum) if minimum is not None else True:
                if len(greatest) >= max:
                    greatest.remove(minimum)
                greatest.append(item)
        return {"success": True, "result": greatest}


    elif json["method"] == "insert":
        db.insert(json["params"])
        return {"success": True, "result": None}

    elif json["method"] == "remove":
        db.remove(Query().fragment(json["params"]))
        return {"success": True, "result": None}

    elif json["method"] == "update":
        db.update(json["params"]["value"], Query().fragment(json["params"]["keys"]))
        return {"success": True, "result": None}

    elif json["method"] == "all":
        return {"success": True, "result": db.all()}

    return {"success": False}


@app.route("/")
async def main(request: request):
    res = handle_req(request)
    if res.get("success"):
        return response.json({
            "result": enc.encrypt(str(res["result"]).encode("utf-8")).decode(),
            "success": True
        })
    else:
        return response.json(res)



if __name__ == "__main__":
    app.run("0.0.0.0", int(os.environ.get("PORT", 5000)))
