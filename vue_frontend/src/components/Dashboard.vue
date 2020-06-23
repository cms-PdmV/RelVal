<template>
  <div>
    <h1 class="page-title">System Dashboard</h1>
    <v-card raised class="page-card">
      <h3 v-if="role('manager')">Settings ({{Object.keys(settings).length}})</h3>
      <small v-if="role('manager')">
        <ul>
          <li v-for="setting in settings" :key="setting._id">{{setting._id}}: <pre>{{JSON.stringify(setting.value, null, 2)}}</pre></li>
        </ul>
      </small>
      <h3 v-if="role('administrator')">Locked objects ({{Object.keys(locks).length}})</h3>
      <small v-if="role('administrator')">
        <ul>
          <li v-for="(info, lock) in locks" :key="lock">{{lock}}: {{info.l}}</li>
        </ul>
      </small>
    </v-card>
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
      locks: [],
      settings: [],
    }
  },
  watch: {
    userInfo: {
      handler: function () {
        this.fetchLocksInfo();
        this.fetchSettings();
      },
      deep: true
    },
  },
  created () {
    this.fetchLocksInfo();
    this.fetchSettings();
    setInterval(this.fetchQueueInfo, 60000);
    setInterval(this.fetchSettings, 60000);
  },
  methods: {
    fetchLocksInfo () {
      if (this.role('administrator')) {
        let component = this;
        axios.get('api/system/locks').then(response => {
          component.locks = response.data.response;
        });
      }
    },
    fetchSettings () {
      if (this.role('manager')) {
        let component = this;
        axios.get('api/settings/get').then(response => {
          component.settings = response.data.response;
        });
      }
    }
  }
}
</script>
