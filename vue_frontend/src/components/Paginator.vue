<template>
  <div>
    <div style="display: inline-block; margin: 10px;">
      Showing {{page * pageSize + 1}} - {{Math.min(totalRows, page * pageSize + pageSize)}} of {{totalRows}}
    </div>
    <div style="display: inline-block;">
      Page Size:
    </div>
    <div class="button-group">
      <button class="button-group-button" v-bind:class="[pageSize === 20 ? 'clicked' : '']" v-on:click="pageSize = 20">20</button>
      <button class="button-group-button" v-bind:class="[pageSize === 50 ? 'clicked' : '']" v-on:click="pageSize = 50">50</button>
      <button class="button-group-button" v-bind:class="[pageSize === 100 ? 'clicked' : '']" v-on:click="pageSize = 100">100</button>
    </div>
    <div style="display: inline-block;">
      Page:
    </div>
    <div class="button-group">
      <button class="button-group-button" v-if="page > 0" v-on:click="page -= 1">
        Previous
      </button>
      <div class="button-group-button">
        Page {{page}}
      </div>
      <button class="button-group-button" v-if="page < (totalRows / pageSize - 1)" v-on:click="page += 1">
        Next
      </button>
    </div>
  </div>
</template>

<script>
  export default {
    props:{
      totalRows: {value: 0},
    },
    data () {
      return {
        pageSize: undefined,
        page: undefined,
        limits: [20, 50, 100]
      }
    },
    created () {
      let query = Object.assign({}, this.$route.query);
      if (!('page' in query)) {
        query['page'] = 0;
      }
      this.page = parseInt(query['page']);
      if (!('limit' in query)) {
        query['limit'] = this.limits[0];
      }
      this.pageSize = parseInt(query['limit']);
      this.$router.replace({query: query}).catch(err => {});
      this.$emit('update', this.page, this.pageSize);
    },
    watch:{
      pageSize: function (newValue, oldValue) {
        if (oldValue !== undefined) {
          this.updateQuery('limit', newValue);
          this.updateQuery('page', this.page);
          this.$emit('update', this.page, newValue);
        }
      },
      page: function (newValue, oldValue) {
        if (oldValue !== undefined) {
          this.updateQuery('page', newValue);
          this.updateQuery('limit', this.pageSize);
          this.$emit('update', newValue, this.pageSize);
        }
      } 
    },
    methods: {
      updateQuery: function(name, value) {
        let query = Object.assign({}, this.$route.query);
        query[name] = value;
        this.$router.replace({query: query}).catch(err => {});
      }
    }
  }
</script>

<style scoped>

.button-group {
  margin: 10px;
  height: 36px;
  border-radius: 6px;
  border: solid 1px #aaa;
  padding: 0;
  display: inline-block;
  color: var(--v-accent-base);
}

.button-group-button {
  display: inline-block;
  padding: 6px 12px;
  line-height: 24px;
  height: 34px;
}

.button-group-button:not(:first-child) {
  border-left: solid 1px #aaa;
}

.clicked {
  background-color: var(--v-accent-base);
  color: white;
  font-weight: 500;
}

</style>