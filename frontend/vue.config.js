const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  pages: {
    index: {
      entry: 'src/main.js',
      title: 'qqplaylist-export'
    }
  },
  devServer: {
    port: 8080,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8081',
        changeOrigin: true
      }
    }
  }
})
