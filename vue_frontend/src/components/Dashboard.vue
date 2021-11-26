<template>
  <div>
    <h1 class="page-title">System Dashboard</h1>
    <v-card raised class="page-card">
      <h3>Submission threads ({{Object.keys(submissionWorkers).length}})</h3>
      <ul>
        <li v-for="(info, worker) in submissionWorkers" :key="worker">Thread "{{worker}}" is {{info.job_name ? 'working on ' + info.job_name + ' for ' + info.job_time + 's' : 'not busy'}}</li>
      </ul>
      <h3 class="mt-3">Submission queue ({{submissionQueue.length}})</h3>
      <ul>
        <li v-for="name in submissionQueue" :key="name"><a :href="'relvals?prepid=' + name" title="Show this RelVal">{{name}}</a> is waiting in queue</li>
      </ul>
      <h3 class="mt-3" v-if="role('administrator')">Build info</h3>
      <ul v-if="role('administrator')">
        <li>Build version: {{buildInfo}}</li>
      </ul>
      <h3 class="mt-3" v-if="role('administrator')">System uptime</h3>
      <ul v-if="role('administrator')">
        <li>{{uptime.days}} days {{uptime.hours}} hours {{uptime.minutes}} minutes {{uptime.seconds}} seconds</li>
      </ul>
      <h3 class="mt-3" v-if="role('administrator')">Settings ({{Object.keys(settings).length}})</h3>
      <small v-if="role('administrator')">
        <ul>
          <li v-for="setting in settings" :key="setting._id">{{setting._id}}: <pre>{{JSON.stringify(setting.value, null, 2)}}</pre></li>
        </ul>
      </small>
      <h3 class="mt-3" v-if="role('administrator')">Locked objects ({{Object.keys(locks).length}})</h3>
      <small v-if="role('administrator')">
        <ul>
          <li v-for="(info, lock) in locks" :key="lock" :style="info ? 'color: red; font-weight: bold;' : ''">{{lock}}: {{info}}</li>
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
      submissionWorkers: [],
      submissionQueue: [],
      locks: [],
      settings: [],
      uptime: {},
      buildInfo: undefined,
      refreshInterval: 60000
    }
  },
  watch: {
    userInfo: {
      handler: function () {
        this.fetchLocksInfo();
        this.fetchSettings();
        this.fetchUptime();
        this.fetchBuildInfo();
      },
      deep: true
    },
  },
  created () {
    this.fetchWorkerInfo();
    this.fetchLocksInfo();
    this.fetchQueueInfo();
    this.fetchSettings();
    this.fetchUptime();
    this.fetchBuildInfo();
    setInterval(this.fetchWorkerInfo, this.refreshInterval);
    setInterval(this.fetchQueueInfo, this.refreshInterval);
    setInterval(this.fetchLocksInfo, this.refreshInterval);
    setInterval(this.fetchSettings, this.refreshInterval);
    setInterval(this.fetchUptime, this.refreshInterval);
    setInterval(this.fetchBuildInfo, this.refreshInterval);
  },
  methods: {
    fetchWorkerInfo () {
      let component = this;
      axios.get('api/system/workers').then(response => {
        component.submissionWorkers = response.data.response;

      });
    },
    fetchQueueInfo () {
      let component = this;
      axios.get('api/system/queue').then(response => {
        component.submissionQueue = response.data.response;

      });
    },
    fetchLocksInfo () {
      if (this.role('administrator')) {
        let component = this;
        axios.get('api/system/locks').then(response => {
          component.locks = response.data.response;
        });
      }
    },
    fetchSettings () {
      if (this.role('administrator')) {
        let component = this;
        axios.get('api/settings/get').then(response => {
          component.settings = response.data.response;
        });
      }
    },
    fetchUptime () {
      if (this.role('administrator')) {
        let component = this;
        axios.get('api/system/uptime').then(response => {
          component.uptime = response.data.response;
        });
      }
    },
    fetchBuildInfo () {
      if (this.role('administrator')) {
        let component = this;
        axios.get('api/system/build_info').then(response => {
          component.buildInfo = response.data.response;
        });
      }
    },
  }
}
</script>
