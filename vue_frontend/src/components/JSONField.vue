<template>
  <div>
    <textarea v-model="internalValue" v-on:input="checkJSON()" :disabled="disabled"></textarea>
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
      value: String,
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
      this.internalValue = this.value;
    },
    watch: {
      internalValue: function(value) {
        this.$emit('input', value);
      },
      value: function(value) {
        this.internalValue = value;
      }
    },
    methods: {
      checkJSON: function() {
        if (!this.internalValue || !this.internalValue.length) {
            this.isJSONValid = true;
            this.errorMessage = undefined;
            return;
        }
        try {
            JSON.parse(this.internalValue);
            this.isJSONValid = true;
            this.errorMessage = undefined;
        } catch(err) {
            this.isJSONValid = false;
            this.errorMessage = err.toString();
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
