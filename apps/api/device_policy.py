"""Device capacity is a server-side role capability, not a client/plan override."""


def unlimited_devices(user):
    return (user.get('role') in ('admin', 'super_admin')
            and user.get('account_status', 'active') not in ('suspended', 'banned')
            and not user.get('extension_access_revoked'))


def device_entitlements(user, entitlements):
    result = {**entitlements, 'devicesUnlimited': unlimited_devices(user)}
    if result['devicesUnlimited']:
        result['deviceLimit'] = None
    return result
