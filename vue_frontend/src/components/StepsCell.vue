<template>
  <div>
    <ul>
      <li v-for="(step, index) in internalData" :key="index">
        {{step.name}}:
        <ul class="monospace">
          <li>CMSSW Release: {{step.cmssw_release}} ({{step.scram_arch}})</li>
          <template v-if="isDriver(step)">
            <li v-if="step.events_per_lumi && step.events_per_lumi.length">Events per Lumi: {{step.events_per_lumi}}</li>
            <li v-if="step.fragment_name && step.fragment_name.length">Fragment: {{step.fragment_name}}</li>
            <li v-if="step.lumis_per_job && step.lumis_per_job.length">Lumis Per Job: {{step.lumis_per_job}}</li>
            <li v-for="(value, key) in step.driver" :key="key">{{key}} {{value}}</li>
          </template>
          <template v-else>
            <li>Dataset: {{step.input.dataset}}</li>
            <li v-if="step.input.lumisection && step.input.lumisection.length">Lumisections and runs: {{step.input.lumisection}}</li>
            <li v-if="step.input.label">Label: {{step.input.label}}</li>
          </template>
        </ul>
        <!-- <pre>{{JSON.stringify(step, null, 2)}}</pre> -->
      </li>
    </ul>
  </div>
</template>

<script>
import { utilsMixin } from '../mixins/UtilsMixin.js'

export default {
  mixins: [utilsMixin],
  props:{
    data: Array
  },
  data () {
    return {
      internalData: []
    }
  },
  watch:{
    data: function (newValue) {
      this.internalData = this.process(newValue);
    }
  },
  created () {
    this.internalData = this.process(this.data);
  },
  methods: {
    process(data) {
      data = this.makeCopy(data);
      data.forEach(step => {
        if (this.isDriver(step)) {
          delete step['input'];
          for (let [key, value] of Object.entries(step.driver)) {
            if (!value || value.length == 0) {
              delete step.driver[key];
              continue
            }
            if (key == 'fragment_name') {
              step.fragment_name = value;
              delete step.driver[key]
              continue
            }
            if (Array.isArray(value)) {
              value = value.join(',');
            }
            if (key == 'extra') {
              step.driver['EXTRA'] = value;
            } else {
              step.driver['--' + key] = value;
            }
            delete step.driver[key];
          }
          if ('EXTRA' in step.driver) {
            let extra = step.driver['EXTRA'];
            delete step.driver['EXTRA'];
            step.driver[''] = extra;
          }
        } else {
          delete step['driver'];
        }
      });
      return data;
    },
    isDriver: function(step) {
      return !step.input || !step.input.dataset || step.input.dataset.length == 0;
    },
  },
}
</script>

<style scoped>

.monospace {
  font-family: monospace;
  font-size: 0.9em;
}

</style>