from flask import Blueprint, jsonify, current_app

ac2_app = Blueprint('ac2_app', __name__)


@ac2_app.route('/MDMServiceConfig')
def mdm_service_config():
    """Apple Configurator 2 checks this route to figure out which enrollment profile it should use."""
    public_hostname = current_app.config.get('PUBLIC_HOSTNAME', 'localhost')
    port = current_app.config.get('PORT', 443)

    return jsonify(
        {
            'dep_enrollment_url': f'https://{public_hostname}:{port}/dep/profile',
            'dep_anchor_certs_url': f'https://{public_hostname}:{port}/dep/anchor_certs',
            'trust_profile_url': f'https://{public_hostname}:{port}/enroll/trust.mobileconfig',
        }
    )
