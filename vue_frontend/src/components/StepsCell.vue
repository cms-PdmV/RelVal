<template>
  <div>
    <ul>
      <li v-for="(step, index) in data" :key="index">
        {{step.name}}:
        <ul>
          <li v-for="(value, key) in stepValues(step)" :key="key" class="monospace">{{key}} {{value}}</li>
        </ul>
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
      stepKeys: function(step) {
        return Object.keys(step).filter(s => step[s] && step[s] !== '' && s != 'driver' && s != 'input');
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
        if (value.input && value.input.dataset && value.input.dataset) {
          for (let key of this.stepKeys(value.input)) {
            newData[this.stepKey(key)] = this.stepValue(value.input[key]);
          }
        } else {
          for (let key of this.stepKeys(value.driver)) {
            newData[this.stepKey(key)] = this.stepValue(value.driver[key]);
          }
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