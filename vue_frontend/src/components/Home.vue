<template>
  <div>
    <h1 class="page-title">Home</h1>
    <v-card raised class="page-card">
      <h3>Objects in RelVal database:</h3>
      <ul>
        <li><a :href="'tickets'">Tickets</a></li>
        <li><a :href="'relvals'">RelVals</a>
          <ul v-if="objectsInfo">
            <li v-for="by_status_entry in objectsInfo.by_status" :key="by_status_entry._id">
              <a :href="'relvals?status=' + by_status_entry._id">{{by_status_entry._id}}</a> - {{by_status_entry.count}} RelVals
              <ul v-if="by_status_entry._id == 'submitted'">
                <li v-for="release_entry in objectsInfo.by_batch" :key="release_entry._id">
                  <a :href="'relvals?status=submitted&cmssw_release=' + release_entry._id">{{release_entry._id}}</a>
                  <ul>
                    <li v-for="batch_entry in release_entry.batches" :key="batch_entry.batch_name">
                      <a :href="'relvals?status=submitted&batch_name=' + batch_entry.batch_name + '&cmssw_release=' + release_entry._id">{{batch_entry.batch_name}}</a> - {{batch_entry.count}} RelVals
                    </li>
                  </ul>
                </li>
              </ul>
            </li>
          </ul>
        </li>
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

