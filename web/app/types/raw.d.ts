// Vite 的 `?raw` 导入（about.md）在运行时由构建器处理；
// Nuxt 生成的 tsconfig 没有带上 vite/client 的类型，这里补一条声明。
declare module '*?raw' {
  const content: string
  export default content
}