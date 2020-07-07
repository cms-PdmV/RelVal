<template>
  <div>
    <h1 class="page-title" v-if="creatingNew"><span class="font-weight-light">Creating</span> new ticket</h1>
    <h1 class="page-title" v-else><span class="font-weight-light">Editing ticket</span> {{prepid}}</h1>
    <v-card raised class="page-card">
      <table v-if="editableObject">
        <tr>
          <td>PrepID</td>
          <td><input type="text" v-model="editableObject.prepid" :disabled="!editingInfo.prepid"></td>
        </tr>
        <tr>
          <td>Campaign</td>
          <td><input type="text" v-model="editableObject.campaign" :disabled="!editingInfo.campaign"></td>
        </tr>
        <tr>
          <td>CPU Cores</td>
          <td><input type="number" v-model="editableObject.cpu_cores" :disabled="!editingInfo.cpu_cores" min="1" max="32"></td>
        </tr>
        <tr>
          <td>Label</td>
          <td><input type="text" v-model="editableObject.label" :disabled="!editingInfo.label"></td>
        </tr>
        <tr>
          <td>Memory</td>
          <td><input type="number" v-model="editableObject.memory" :disabled="!editingInfo.memory" min="0" max="64000" step="1000"></td>
        </tr>
        <tr>
          <td>Notes</td>
          <td><textarea v-model="editableObject.notes" :disabled="!editingInfo.notes"></textarea></td>
        </tr>
        <tr>
          <td>Recycle GS</td>
          <td><input type="checkbox" v-model="editableObject.recycle_gs" :disabled="!editingInfo.recycle_gs"/></td>
        </tr>
        <tr>
          <td>RelVal set</td>
          <td>
            <select v-model="editableObject.relval_set" :disabled="!editingInfo.relval_set">
              <option>standard</option>
              <option>upgrade</option>
              <option>generator</option>
              <option>pileup</option>
              <option>premix</option>
            </select>
          </td>
        </tr>
        <tr>
          <td>Sample Tag</td>
          <td><input type="text" v-model="editableObject.sample_tag" :disabled="!editingInfo.sample_tag"></td>
        </tr>
        <tr>
          <td>Workflows ({{listLength(editableObject.workflow_ids)}})</td>
          <td><textarea v-model="editableObject.workflow_ids" :disabled="!editingInfo.workflow_ids"></textarea></td>
        </tr>
      </table>
      <v-btn small class="mr-1 mb-1" color="primary" @click="save()">Save</v-btn>
    </v-card>
    <LoadingOverlay :visible="loading"/>
    <v-dialog v-model="errorDialog.visible"
              max-width="50%">
      <v-card>
        <v-card-title class="headline">
          {{errorDialog.title}}
        </v-card-title>
        <v-card-text>
          {{errorDialog.description}}
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn small class="mr-1 mb-1" color="primary" @click="clearErrorDialog()">
            Dismiss
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>

import axios from 'axios'
import { utilsMixin } from '../mixins/UtilsMixin.js'
import LoadingOverlay from './LoadingOverlay.vue'

export default {
  name: 'TicketsEdit',
  components: {
    LoadingOverlay
  },
  mixins: [
    utilsMixin
  ],
  data () {
    return {
      prepid: undefined,
      editableObject: {},
      editingInfo: {},
      loading: true,
      creatingNew: true,
      errorDialog: {
        visible: false,
        title: '',
        description: '',
      }
    }
  },
  created () {
    let query = Object.assign({}, this.$route.query);
    if (query.prepid && query.prepid.length) {
      this.prepid = query.prepid;
    } else {
      this.prepid = '';
    }
    this.creatingNew = this.prepid.length == 0;
    this.loading = true;
    let component = this;
    axios.get('api/tickets/get_editable/' + this.prepid).then(response => {
      if (query.clone && query.clone.length) {
        axios.get('api/tickets/get_editable/' + query.clone).then(templateResponse => {
          templateResponse.data.response.object.prepid = response.data.response.object.prepid;
          templateResponse.data.response.object.history = response.data.response.object.history;
          templateResponse.data.response.object.status = response.data.response.object.status;
          templateResponse.data.response.object.created_relvals = response.data.response.object.created_relvals;
          component.editableObject = templateResponse.data.response.object;
          component.editableObject.workflow_ids = component.editableObject.workflow_ids.filter(Boolean).join('\n');
          component.editingInfo = response.data.response.editing_info;
          component.loading = false;
        }).catch(error => {
          component.loading = false;
          console.log(error);
          this.showError('Error fetching editing information', error.response.data.message);
        });
      } else {
        component.editableObject = response.data.response.object;
        component.editableObject.workflow_ids = component.editableObject.workflow_ids.filter(Boolean).join('\n');
        component.editingInfo = response.data.response.editing_info;
        component.loading = false;
      }
    }).catch(error => {
      component.loading = false;
      console.log(error);
      this.showError('Error fetching editing information', error.response.data.message);
    });
  },
  methods: {
    save: function() {
      this.loading = true;
      let editableObject = this.makeCopy(this.editableObject);
      editableObject.notes = editableObject.notes.trim();
      editableObject.workflow_ids = editableObject.workflow_ids.replace(/,/g, '\n').split('\n').map(function(s) { return s.trim() }).filter(Boolean);
      let httpRequest;
      if (this.creatingNew) {
        httpRequest = axios.put('api/tickets/create', editableObject);
      } else {
        httpRequest = axios.post('api/tickets/update', editableObject);
      }
      let component = this;
      httpRequest.then(response => {
        component.loading = false;
        window.location = 'tickets?prepid=' + response.data.response.prepid;
      }).catch(error => {
        component.loading = false;
        this.showError('Error saving ticket', error.response.data.message);
      });
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
  }
}
</script>
