<template>
  <div>
    <textarea v-model="internalValue" v-on:blur="reformat()" :disabled="disabled"></textarea>
    <template v-if="this.internalValue && this.internalValue.length">
      <br>
      <small v-if="isJSONValid" style="color: #27ae60">Valid JSON</small>
      <small v-else style="color: red">Invalid JSON: {{errorMessage}}</small>
    </template>
  </div>
</template>

<script>
/* component needs to do to be compatible with v-model
   is accept a :value property and emit an @input event
   when the user changes the value.
*/
  export default {
    props:{
      value: Object,
      disabled: {
        type: Boolean,
        default: false,
      }
    },
    data () {
      return {
        internalValue: undefined,
        isJSONValid: true,
        errorMessage: undefined,
      }
    },
    created () {
      if (this.value) {
        this.internalValue = JSON.stringify(this.value, null, 2);
      } else {
        this.internalValue = undefined;
      }
    },
    watch: {
      internalValue: function() {
        if (!this.internalValue || !this.internalValue.length) {
            this.isJSONValid = true;
            this.errorMessage = undefined;
            this.$emit('input', {});
            return;
        }
        try {
            let parsedValue = JSON.parse(this.internalValue);
            this.isJSONValid = true;
            this.errorMessage = undefined;
            this.$emit('input', parsedValue);
        } catch(err) {
            this.isJSONValid = false;
            this.errorMessage = err.toString();
        }
      },
      value: function(value) {
        if (!this.internalValue) {
          this.internalValue = JSON.stringify(value, null, 2);
        }
      }
    },
    methods: {
      reformat: function() {
        if (this.isJSONValid) {
          this.internalValue = JSON.stringify(JSON.parse(this.internalValue), null, 2);
        }
      },
    },
  }
</script>

<style scoped>
textarea {
  font-family: monospace;
  font-size: 0.85em;
}
</style>
