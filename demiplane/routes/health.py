def register_health_routes(app, limiter, talisman):
    @app.route('/health')
    @limiter.exempt
    @talisman(force_https=False)
    def health_check():
        return 'ok', 200
