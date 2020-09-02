<template>
  <div style="height: calc(100vh - 128px); overflow: auto;">
    <div style="display: flex;">
      <div style="flex: 1 1 auto;">
        <div>
          <div style="width: calc(100vw - 32px); position: sticky; left: 16px;">
            <h1 class="page-title">Campaigns</h1>
            <ColumnSelector :columns="columns"
                            v-on:updateColumns="updateTableColumns"/>
          </div>
        </div>
        <v-data-table :headers="headers"
                      :items="dataItems"
                      :items-per-page="itemsPerPage"
                      :loading="loading"
                      disable-sort
                      hide-default-footer
                      class="elevation-1">
          <template v-slot:item._actions="{ item }">
            <a :href="'campaigns/edit?prepid=' + item.prepid" v-if="role('manager')" title="Edit campaign">Edit</a>&nbsp;
            <a style="text-decoration: underline;" @click="showDeleteDialog(item)" v-if="role('manager')" title="Delete campaign">Delete</a>&nbsp;
            <a :href="'tickets/edit?campaign=' + item.prepid" v-if="role('manager')" title="Create ticket">Create ticket</a>&nbsp;
            <a :href="'relvals?campaign=' + item.prepid" title="Show all RelVals in this campaign">Show RelVals</a>&nbsp;
            <a :href="'tickets?campaign=' + item.prepid" title="Show all Tickets in this campaign">Show tickets</a>&nbsp;
          </template>
          <template v-slot:item.prepid="{ item }">
            <a :href="'campaigns?prepid=' + item.prepid" title="Show only this campaign">{{item.prepid}}</a>
          </template>
          <template v-slot:item.cmssw_release="{ item }">
            <a :href="'campaigns?cmssw_release=' + item.cmssw_release" :title="'Show all campaigns with ' + item.cmssw_release">{{item.cmssw_release.replace('_', ' ').replace(/_/g, '.')}}</a>
          </template>
          <template v-slot:item.notes="{ item }">
            <pre v-if="item.notes.length" class="notes">{{item.notes}}</pre>
          </template>
          <template v-slot:item.history="{ item }">
            <HistoryCell :data="item.history"/>
          </template>
        </v-data-table>
      </div>
    </div>

    <v-dialog v-model="dialog.visible"
              max-width="50%">
      <v-card>
        <v-card-title class="headline">
          {{dialog.title}}
        </v-card-title>
        <v-card-text>
          {{dialog.description}}
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn small class="mr-1 mb-1" color="primary" @click="dialog.cancel">
            Cancel
          </v-btn>
          <v-btn small class="mr-1 mb-1" color="error" @click="dialog.ok">
            OK
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="errorDialog.visible"
              max-width="50%">
      <v-card>
        <v-card-title class="headline">
          {{errorDialog.title}}
        </v-card-title>
        <v-card-text>
          <span v-html="errorDialog.description"></span>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn small class="mr-1 mb-1" color="primary" @click="errorDialog.visible = false">
            Dismiss
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <footer>
      <a :href="'campaigns/edit'" v-if="role('manager')" title="Create new campaign">New campaign</a>
      <Paginator :totalRows="totalItems"
                 v-on:update="onPaginatorUpdate"/>
    </footer>
  </div>
</template>

<script>

import axios from 'axios'
import ColumnSelector from './ColumnSelector'
import Paginator from './Paginator'
import HistoryCell from './HistoryCell'
import { roleMixin } from '../mixins/UserRoleMixin.js'
import { utilsMixin } from '../mixins/UtilsMixin.js'

export default {
  components: {
    ColumnSelector,
    Paginator,
    HistoryCell
  },
  mixins: [roleMixin, utilsMixin],
  data () {
    return {
      databaseName: undefined,
      columns: [
        {'dbName': 'prepid', 'displayName': 'PrepID', 'visible': 1},
        {'dbName': '_actions', 'displayName': 'Actions', 'visible': 1},
        {'dbName': 'batch_name', 'displayName': 'Batch name', 'visible': 1},
        {'dbName': 'cmssw_release', 'displayName': 'CMSSW Version', 'visible': 1},
        {'dbName': 'notes', 'displayName': 'Notes', 'visible': 1},
        {'dbName': 'history', 'displayName': 'History', 'visible': 0},
      ],
      headers: [],
      dataItems: [],
      loading: false,
      itemsPerPage: 1,  // If initial value is 0, table does not appear after update
      totalItems: 0,
      dialog: {
        visible: false,
        title: '',
        description: '',
        cancel: undefined,
        ok: undefined,
      },
      errorDialog: {
        visible: false,
        title: '',
        description: ''
      }
    }
  },
  created () {
    this.clearDialog();
  },
  methods: {
    fetchObjects () {
      let component = this;
      this.loading = true;
      let query = this.$route.query;
      let queryParams = '';
      Object.keys(query).forEach(k => {
        if (k != 'shown') {
          queryParams += '&' + k + '=' + query[k];
        }
      });
      axios.get('api/search?db_name=campaigns' + queryParams).then(response => {
        component.dataItems = response.data.response.results.map(function (x) { x._actions = undefined; return x});
        component.totalItems = response.data.response.total_rows;
        component.loading = false;
      }).catch(error => {
        component.loading = false;
        component.clearDialog();
        component.showError("Error fetching campaigns", component.getError(error));
      });
    },
    updateTableColumns: function(columns, headers) {
      this.columns = columns;
      this.headers = headers;
    },
    onPaginatorUpdate: function(page, itemsPerPage) {
      this.itemsPerPage = itemsPerPage;
      this.fetchObjects();
    },
    clearDialog: function() {
      this.dialog.visible = false;
      this.dialog.title = '';
      this.dialog.description = '';
      this.dialog.ok = function() {};
      this.dialog.cancel = function() {};
    },
    clearErrorDialog: function() {
      this.errorDialog.visible = false;
      this.errorDialog.title = '';
      this.errorDialog.description = '';
    },
    showError: function(title, description) {
      this.clearErrorDialog();
      this.errorDialog.title = title;
      this.errorDialog.description = description;
      this.errorDialog.visible = true;
    },
    showDeleteDialog: function(campaign) {
      let component = this;
      this.dialog.title = "Delete " + campaign.prepid + "?";
      this.dialog.description = "Are you sure you want to delete " + campaign.prepid + " campaign?";
      this.dialog.ok = function() {
        component.loading = true;
        axios.delete('api/campaigns/delete', {data: {'prepid': campaign.prepid}}).then(() => {
          component.clearDialog();
          component.fetchObjects();
        }).catch(error => {
          component.loading = false;
          component.clearDialog();
          component.showError("Error deleting campaign", component.getError(error));
        });
      }
      this.dialog.cancel = function() {
        component.clearDialog();
      }
      this.dialog.visible = true;
    }
  }
}
</script>
