<template>
  <div class="subcampaigns">
    <h1>Home</h1>
    <div style="margin: 8px">
      <h3>RelVal objects:</h3>
      <ul>

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
      objectsInfo: undefined
    }
  },
  created () {
    this.fetchObjectsInfo();
  },
  methods: {
    fetchObjectsInfo () {
      let component = this;
      axios.get('api/system/objects_info').then(response => {
        component.objectsInfo = response.data.response;

      });
    },
  }
}
</script>

<style scoped>

h1 {
  margin: 8px;
}

</style>
