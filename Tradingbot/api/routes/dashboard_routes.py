"""
Dashboard routes for Tradingbot API.
Handles the web UI and static files.
"""

import os
from flask import send_file, redirect, url_for, send_from_directory
import logging

logger = logging.getLogger(__name__)


def register_routes(app):
    """Register dashboard-related routes with Flask app"""
    
    @app.route("/")
    def root():
        """Redirect to dashboard"""
        return redirect(url_for("serve_dashboard"))
    
    @app.route("/dashboard")
    def serve_dashboard():
        """Serve the main dashboard HTML"""
        dashboard_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "dashboard.html"
        )
        return send_file(dashboard_path)
    
    @app.route("/<path:filename>")
    def serve_static(filename):
        """Serve static files (JS, CSS) from the Tradingbot directory"""
        static_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        if filename.endswith(".js") or filename.endswith(".css"):
            return send_from_directory(static_dir, filename)
        # Fallback: 404
        return "Not found", 404