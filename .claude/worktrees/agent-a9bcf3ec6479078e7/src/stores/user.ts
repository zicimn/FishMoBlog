import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    id: Number(localStorage.getItem('id') || 0),
    username: localStorage.getItem('username') || '',
    token: localStorage.getItem('token') || ''
  }),
  getters: {
    isLoggedIn: (state) => !!state.token
  },
  actions: {
    login(user: {
      id: number
      username: string
      access_token: string
      avatar?: string
    }) {
      this.id = user.id
      this.username = user.username
      this.token = user.access_token
      localStorage.setItem('token', user.access_token)
      localStorage.setItem('id', user.id.toString())
      localStorage.setItem('username', user.username)
    },
    logout() {
      this.id = 0
      this.username = ''
      this.token = ''
      localStorage.removeItem('token')
      localStorage.removeItem('id')
      localStorage.removeItem('username')
    }
  }
})
