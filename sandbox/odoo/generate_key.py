# Run inside the Odoo container with `odoo shell` (see README). Prints one line: an API key for the admin user,
# scope 'rpc', valid 30 days. The key is written by setup.sh into .env.local (git-ignored), never into git.
import datetime
user = env.ref("base.user_admin")  # noqa: F821 (env is provided by odoo shell)
exp = datetime.datetime.now() + datetime.timedelta(days=30)
key = env["res.users.apikeys"].with_user(user)._generate("rpc", "sentinelloop-sandbox", exp)  # noqa: F821
env.cr.commit()  # noqa: F821
print("SENTINELLOOP_ODOO_KEY=" + key)
