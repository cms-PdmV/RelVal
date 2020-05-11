<template>
  <div>
    <h1>System Dashboard</h1>
    <div style="margin: 8px">

    </div>
  </div>
</template>

<script>

import axios from 'axios'
import { roleMixin } from '../mixins/UserRoleMixin.js'

export default {
  components: {
  },
  mixins: [roleMixin],
  data () {
    return {
    }
  },
  created () {

  },
  methods: {

  }
}
</script>

<style scoped>

h1 {
  margin: 8px;
}

</style>
