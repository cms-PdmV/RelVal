<template>
  <div>
    <h1 class="page-title">System Dashboard</h1>
    <v-card raised class="page-card">
      <h3>Submission threads ({{Object.keys(submission_workers).length}})</h3>
      <ul>
        <li v-for="(info, worker) in submission_workers" :key="worker">"{{worker}}" is
          <template v-if="info.job_name">
            working on <a :href="'relvals?prepid=' + info.job_name" title="Show this RelVal">{{info.job_name}}</a> for {{info.job_time}}s
          </template>
          <template v-else>
            not busy
          </template>
        </li>
      </ul>
      <h3 class="mt-3">Submission queue ({{submission_queue.length}})</h3>
      <ul>
        <li v-for="name in submission_queue" :key="name"><a :href="'relvals?prepid=' + name" title="Show this RelVal">{{name}}</a> is waiting in queue</li>
      </ul>
      <h3 class="mt-3" v-if="role('manager')">Settings ({{Object.keys(settings).length}})</h3>
      <small v-if="role('manager')">
        <ul>
          <li v-for="setting in settings" :key="setting._id">{{setting._id}}: <pre>{{JSON.stringify(setting.value, null, 2)}}</pre></li>
        </ul>
      </small>
      <h3 class="mt-3" v-if="role('administrator')">Locked objects ({{Object.keys(locks).length}})</h3>
      <small v-if="role('administrator')">
        <ul>
          <li v-for="(info, lock) in locks" :key="lock">{{lock}}: {{info}}</li>
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
      submission_workers: [],
      submission_queue: [],
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
    this.fetchWorkerInfo();
    this.fetchLocksInfo();
    this.fetchQueueInfo();
    this.fetchSettings();
    setInterval(this.fetchWorkerInfo, 60000);
    setInterval(this.fetchQueueInfo, 60000);
    setInterval(this.fetchLocksInfo, 60000);
    setInterval(this.fetchSettings, 60000);
  },
  methods: {
    fetchWorkerInfo () {
      let component = this;
      axios.get('api/system/workers').then(response => {
        component.submission_workers = response.data.response;

      });
    },
    fetchQueueInfo () {
      let component = this;
      axios.get('api/system/queue').then(response => {
        component.submission_queue = response.data.response;

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
