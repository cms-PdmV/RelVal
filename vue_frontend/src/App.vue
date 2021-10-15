<template>
  <v-app>
    <v-app-bar app>
      <a href="" class="no-decoration">
        <v-toolbar-title class="headline">
          <span>Rel</span>
          <span class="font-weight-light">Val</span>
        </v-toolbar-title>
      </a>
      <v-spacer></v-spacer>
      <v-btn
        text
        class="mr-2"
        href="tickets">
        <span>Tickets</span>
      </v-btn>
      <v-btn
        text
        class="mr-2"
        href="relvals">
        <span>RelVals</span>
      </v-btn>
      <v-btn
        text
        class="mr-2"
        href="dashboard">
        <span>Dashboard</span>
      </v-btn>
      <v-spacer></v-spacer>
      <div v-if="userInfo">
        <span :title="'Username: ' + userInfo.username + '\nRole: ' + userInfo.role"><small>Logged in as</small> {{userInfo.fullname}} </span>
        <img class="admin-star" :title="'User role: ' + userInfo.role" :src="userRolePicture"/>
      </div>
    </v-app-bar>
    <v-main class="content-container">
      <router-view/>
    </v-main>
  </v-app>
</template>

<script>

import { roleMixin } from './mixins/UserRoleMixin.js'

export default {
  name: 'App',

  mixins: [
    roleMixin
  ],
  computed: {
    userRolePicture: function() {
      if (this.userInfo.role_index == 1) {
        return 'static/star.png';
      }
      if (this.userInfo.role_index == 2) {
        return 'static/admin_star.png';
      }
      return 'static/invisible.png';
    }
  }
};
</script>

<style scoped>

header {
  background: var(--v-background-base) !important;
}

.content-container {
  background: var(--v-backBackground-base);
}

.headline {
  color: rgba(0, 0, 0, 0.87) !important;
}

a.no-decoration {
  text-decoration: none;
}

.admin-star {
  width: 16px;
  height: 16px;
}

</style>

<style>

html {
  overflow: auto !important;
}

footer {
  padding: 0 12px;
  height: 52px;
  left: 0px;
  right: 0px;
  bottom: 0px;
  position: fixed;
  background: var(--v-background-base) !important;
  box-shadow: 0px -2px 4px -1px rgba(0, 0, 0, 0.2), 0px -4px 5px 0px rgba(0, 0, 0, 0.14), 0px -1px 10px 0px rgba(0, 0, 0, 0.12);
}

table {
  white-space: nowrap;
}

.notes, .fragment {
  font-size: 0.85em;
  font-style: monospace;
  margin: 4px;
  padding: 4px;
  border: 1px solid rgba(0, 0, 0, 0.5);
}

.v-data-table__wrapper {
  overflow-x: visible !important;
  overflow-y: visible !important;
}

.v-application th.text-start {
  color: rgba(0,0,0,0.87) !important;
  font-size: 0.9em !important;
}

.mdi-checkbox-marked::before {
  color: var(--v-accent-base) !important
}

.theme--light.v-label {
  color: rgba(0,0,0,0.87) !important;
}

h1.page-title {
  text-align: center;
  margin: 8px 16px;
}

.page-card {
  margin: auto;
  margin-bottom: 16px;
  padding: 16px;
  max-width: 850px !important;
}

.page-card table {
  width: 100%;
  border-spacing: 0;
}

.page-card th,
.page-card td {
  padding: 6px 0;
}

.page-card td:nth-child(2) {
  width: 100%;
}

.page-card td:nth-child(1) {
  padding-right: 16px;
}

.page-card input,
.page-card select,
.page-card textarea {
  border: 1px solid rgba(0, 0, 0, 0.87);
  border-radius: 4px;
  background: #fbfbfb;
}

.page-card input[type="text"],
.page-card textarea {
  width: 100%;
  padding: 0 4px;
}

.page-card textarea {
  min-height: 200px;
}

.page-card input[type="number"] {
  width: 45%;
  text-align: right;
  padding: 0 0 0 4px;
  margin-right: 4px;
}

.page-card select {
  width: 45%;
  height: 25.625px;
  appearance: menulist;
  padding: 0 4px;
}

.page-card input:disabled,
.page-card select:disabled,
.page-card textarea:disabled {
  background: #dadada !important;
  color: rgba(0, 0, 0, 0.65);
  cursor: not-allowed;
  opacity: 1;
}

@media all and (max-width:650px){
  .page-card td{
      display: block;
      width: 100%;
      padding: 1px 0;
  }
  .page-card tr{
      display: block;
      margin-bottom: 6px;
  }
}

a {
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

.actions > a:not(:last-of-type):after {
  color: rgba(0,0,0,0.87);
  content: "|";
  margin-left: 3px;
  margin-right: 3px;
  display: inline-block
}

</style>
