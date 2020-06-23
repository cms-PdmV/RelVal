<template>
  <v-overlay :absolute="false"
              :opacity="0.95"
              :z-index="3"
              :value="visible"
              style="text-align: center">
    <v-progress-circular indeterminate color="primary"></v-progress-circular>
    <br>Please wait...
  </v-overlay>
</template>

<script>

export default {

  props: {
    visible: { 
      type: Boolean,
      default: true
    }
  }
}

</script>