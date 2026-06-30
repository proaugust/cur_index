import { defineConfig, type Plugin } from 'vite';
import vue from '@vitejs/plugin-vue';
import VueSetupExtend from 'vite-plugin-vue-setup-extend';
import AutoImport from 'unplugin-auto-import/vite';
import Components from 'unplugin-vue-components/vite';
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers';

/** Vite 3 dev：根路径 / 有时不落 index.html，显式改写 */
function devRootIndexFallback(): Plugin {
	return {
		name: 'dev-root-index-fallback',
		enforce: 'pre',
		apply: 'serve',
		configureServer(server) {
			server.middlewares.use((req, _res, next) => {
				if (req.url === '/' || req.url === '') {
					req.url = '/index.html';
				}
				next();
			});
		},
	};
}

export default defineConfig(({ command }) => ({
	base: command === 'build' ? './' : '/',
	plugins: [
		devRootIndexFallback(),
		vue(),
		VueSetupExtend(),
		AutoImport({
			resolvers: [ElementPlusResolver()]
		}),
		Components({
			resolvers: [ElementPlusResolver()]
		})
	],
	optimizeDeps: {
		include: [
			'schart.js',
			'echarts/core',
			'echarts/charts',
			'echarts/components',
			'echarts/renderers',
			'vue-echarts',
		],
		// face-api 体积大，仅在人脸打卡页按需加载，不阻塞其他页面
		exclude: ['@vladmandic/face-api'],
	},
	build: {
		rollupOptions: {
			output: {
				manualChunks(id) {
					if (id.includes('@vladmandic/face-api')) return 'face-api';
					if (id.includes('node_modules/echarts')) return 'echarts';
					if (id.includes('api-debug-panel')) return 'api-debug';
				},
			},
		},
	},
	resolve: {
		alias: {
			'@': '/src',
			'~': '/src/assets'
		}
	},
	define: {
		__VUE_PROD_HYDRATION_MISMATCH_DETAILS__: "true",
	},
	server: {
		port: 5173,
		watch: {
			ignored: ['**/node_modules/**', '**/.git/**'],
		},
		proxy: {
			'/api': {
				target: 'http://127.0.0.1:8000',
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api/, ''),
			},
		},
	},
}));
