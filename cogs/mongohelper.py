# DNI

def find(collection, _id):
    try:
        entry = list(collection.find({"_id": _id}))[0]
    except IndexError:
        return None
    return entry


def add(collection, entry):
    collection.insert_one(entry)


def update(collection, _id, post):
    collection.update_one({"_id": _id}, {"$set": post}, upsert=True)