import os
from webapp import app

# Run a test server.
app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5001)), debug=True)