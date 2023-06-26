#!/usr/bin/python3

import os
import flask
import werkzeug
import argparse
import sys
import json
import datetime
import yaml

import sqlalchemy
from sqlalchemy import Column, Integer, String, Boolean, or_, and_, asc, desc
from flask_sqlalchemy import SQLAlchemy

XAUTH_GROUPS_SEP = ","
TILES_CONFIG_FILE_PATH = "config.yaml"

app = flask.Flask("Atlantis Hub")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLITE_LOCATION") or "sqlite:///sqlite.db"
db = SQLAlchemy(app)

class Tile(db.Model):

    __tablename__ = "tiles"

    name        = Column(String, primary_key=True)
    common_name = Column(String)
    href        = Column(String)

def parse_xauth_groups(groups_string):

    if not groups_string:
        return []
    
    # format ist like this group1,group2,role:role1,role:role2,...
    # lets ignore the roles for now
    return filter(lambda x: "role:" not in x, groups_string.split(XAUTH_GROUPS_SEP))

def parse_tiles_file():

    with open(TILES_CONFIG_FILE_PATH) as f:
        return yaml.safe_load(f)

def filter_tiles_by_groups(tiles, groups):
    '''Remove all tiles that are not covered by the users groups'''
    return filter(lambda tile: not tile.get("groups") or tile.get("groups") in groups, tiles)

@app.route("/")
def list():
    user = flask.request.headers.get("X-Forwarded-Preferred-Username")
    groups = parse_xauth_groups(flask.request.headers.get("X-Auth-Request-Groups"))

    tiles = parse_tiles_file()
    tiles_filtered = filter_tiles_by_groups(tiles, groups)

    return flask.render_template("dashboard.html", tiles) # TODO use filtered tiles after testing

def create_app():
    db.create_all()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='AtlantisHub Server',
                        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # general parameters #
    parser.add_argument("-i", "--interface", default="127.0.0.1", help="Interface to listen on")
    parser.add_argument("-p", "--port",      default="5000",      help="Port to listen on")
    args = parser.parse_args()

    # startup #
    with app.app_context():
        create_app()

    app.run(host=args.interface, port=args.port)
