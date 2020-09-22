<template>
  <div>
    <ul>
      <li v-for="(step, index) in data" :key="index">
        {{step.name}}:
        <ul class="monospace">
          <li>CMSSW Release: {{step.cmssw_release}} ({{step.scram_arch}})</li>
          <template v-if="isDriver(step)">
            <li v-if="step.events_per_lumi && step.events_per_lumi.length">Events per Lumi: {{step.events_per_lumi}}</li>
            <li v-if="step.driver.type && step.driver.type.length">Type: {{step.driver.type}}</li>
            <li v-if="step.lumis_per_job && step.lumis_per_job.length">Lumis Per Job: {{step.lumis_per_job}}</li>
            <li v-for="(value, key) in stepValues(step.driver)" :key="key">{{key}} {{value}}</li>
          </template>
          <template v-else>
            <li>Dataset: {{step.input.dataset}}</li>
            <li>Lumisections and runs: {{step.input.lumisection}}</li>
            <li>Label: {{step.input.label}}</li>
          </template>
        </ul>
        <!-- <pre>{{JSON.stringify(step, null, 2)}}</pre> -->
      </li>
    </ul>
  </div>
</template>

<script>

  export default {
    props:{
      data: Array
    },
    data () {
      return {
      }
    },
    methods: {
      cleanUpDict: function(dict) {
        for (let key in dict) {
          if (dict[key] == "") {
            delete dict[key];
          } else if (Array.isArray(dict[key])) {
            dict[key] = dict[key].join(',');
          }
        }
      },
      isDriver: function(step) {
        return !step.input.dataset || step.input.dataset.length == 0;
      },
      stepKeys: function(step) {
        return Object.keys(step).filter(s => step[s] && step[s] !== '' && s != 'driver' && s != 'input' && s != 'type');
      },
      stepKey: function(key) {
        return key == 'extra' ? 'EXTRA: ' : '--' + key;
      },
      stepValue: function(value) {
        if (Array.isArray(value)) {
          return value.join(',');
        } else if (value === true || value === false) {
          return '';
        }
        return value;
      },
      stepValues: function(value) {
        let newData = {};
        for (let key of this.stepKeys(value)) {
          newData[this.stepKey(key)] = this.stepValue(value[key]);
        }
        return newData;
      }
    },
    computed: {
    }
  }
</script>

<style scoped>

.monospace {
  font-family: monospace;
  font-size: 0.9em;
}

</style>