<template>
  <div>
    <h1>Home</h1>
    <div style="margin: 8px">
      <h3>RelVal objects:</h3>
      <ul>
        <li><a :href="'tickets'">Tickets</a></li>
        <li><a :href="'relvals'">RelVals</a></li>
      </ul>
    </div>
  </div>
</template>

<script>

import axios from 'axios'

export default {
  name: 'home',
  components: {
    // HelloWorld
  },
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
