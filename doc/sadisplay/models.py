import os
import codecs
import sadisplay
from flask import Flask

from commandment.models import db, Device, Command, InstalledApplication, InstalledCertificate, \
    InstalledProfile
from commandment.pki.models import Certificate

dummyapp = Flask(__name__)
db.init_app(dummyapp)

UML_PATH = os.path.realpath(
    f'{os.path.dirname(__file__)}/../_static/uml/models'
)


classes = [Certificate, Command, InstalledApplication, InstalledApplication, InstalledCertificate, InstalledProfile]

with dummyapp.app_context():
    for cls in classes:
        desc = sadisplay.describe(
            [getattr(cls, attr) for attr in dir(cls)],
            show_methods=True,
            show_properties=True,
            show_indexes=True,
        )

        with codecs.open(os.path.join(UML_PATH, f'{cls.__name__}.plantuml'), 'w', encoding='utf-8') as f:
            f.write(sadisplay.plantuml(desc))
