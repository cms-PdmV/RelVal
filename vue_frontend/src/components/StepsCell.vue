<template>
  <div>
    <ul>
      <li v-for="step in this.data" :key="step.name">
      {{step.name}}
      <small><pre>{{JSON.stringify(step, null, 2)}}</pre></small>
      </li>
    </ul>
  </div>
</template>

<script>

  export default {
    props:{
      data: {
        type: Array
      }
    },
    data () {
      return {
      }
    },
    created () {
    },
    watch:{
    },
    methods: {

    },
    computed: {
      shortenedStep: function() {
        let data = [];
        for (let step of this.data) {
          let s = {};
          for (let attr in step) {
            if (step[attr] == false) {
              continue;
            }
            if (step[attr] == true) {
              s[attr] = step[attr];
              continue;
            }
            if (step[attr].length) {
              s[attr] = step[attr]
            }
          }
          data.push(s);
        }
        return data;
      }
    }
  }
</script>