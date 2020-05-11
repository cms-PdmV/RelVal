const isProd = process.env.NODE_ENV === "production"

module.exports = {
  "transpileDependencies": [
    "vuetify"
  ],
  publicPath: isProd ? '/relval' : '',
  assetsDir: 'static/'
}
