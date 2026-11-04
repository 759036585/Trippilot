/// <reference types="vite/client" />

// 自定义的环境变量类型声明，对应根目录的 .env.local
interface ImportMetaEnv {
  /** 后端接口地址，例如 http://127.0.0.1:8000 */
  readonly VITE_API_BASE_URL: string
  /** 高德地图 Web端(JS API) Key */
  readonly VITE_AMAP_JS_KEY: string
  /** 高德地图安全密钥 */
  readonly VITE_AMAP_SECURITY_CODE: string
}
