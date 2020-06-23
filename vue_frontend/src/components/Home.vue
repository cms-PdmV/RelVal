<template>
  <div>
    <h1 class="page-title">Home</h1>
    <v-card raised class="page-card">
      <h3>Objects in RelVal database:</h3>
      <ul>
        <li><a :href="'tickets'">Tickets</a></li>
        <li><a :href="'relvals'">RelVals</a></li>
      </ul>
    </v-card>
  </div>
</template>

<script>

import axios from 'axios'

export default {
  name: 'home',
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

