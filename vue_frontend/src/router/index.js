import Vue from 'vue'
import VueRouter from 'vue-router'
import Home from '@/components/Home'
import Dashboard from '@/components/Dashboard'
import qs from 'qs';


Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    name: 'home',
    component: Home
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: Dashboard
  }
]

const router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  stringifyQuery: query => {
    var result = qs.stringify(query);
    // Do not encode asterisks
    result = result.replace(/%2A/g, '*').replace(/%2F/g, '/').replace(/%21/g, '!');
    return result ? ('?' + result) : '';
  },
  routes
})

export default router
