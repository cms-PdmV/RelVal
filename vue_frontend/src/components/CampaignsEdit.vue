<template>
  <div>
    <h1 class="page-title" v-if="creatingNew"><span class="font-weight-light">Creating</span> new campaign</h1>
    <h1 class="page-title" v-else><span class="font-weight-light">Editing campaign</span> {{prepid}}</h1>
    <v-card raised class="page-card">
      <table v-if="editableObject">
        <tr>
          <td>PrepID</td>
          <td><input type="text" v-model="editableObject.prepid" :disabled="!editingInfo.prepid"></td>
        </tr>
        <tr>
          <td>Batch name</td>
          <td><input type="text" v-model="editableObject.batch_name" placeholder="E.g. fullsim_noPU_..." :disabled="!editingInfo.batch_name"></td>
        </tr>
        <tr>
          <td>CMSSW Version</td>
          <td><input type="text" v-model="editableObject.cmssw_release" placeholder="E.g. CMSSW_11_..." :disabled="!editingInfo.cmssw_release"></td>
        </tr>
        <tr>
          <td>Notes</td>
          <td><textarea v-model="editableObject.notes" placeholder="E.g. Goals, comments, links to TWiki and HN" :disabled="!editingInfo.notes"></textarea></td>
        </tr>
      </table>
      <v-btn small class="mr-1 mt-1" color="primary" @click="save()">Save</v-btn>
      <v-btn small class="mr-1 mt-1" color="error" @click="cancel()">Cancel</v-btn>
    </v-card>
    <LoadingOverlay :visible="loading"/>
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
  mixins: [
    utilsMixin
  ],
  components: {
    LoadingOverlay
  },
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
    axios.get('api/campaigns/get_editable/' + this.prepid).then(response => {
      component.editableObject = response.data.response.object;
      component.editingInfo = response.data.response.editing_info;
      component.loading = false;
    }).catch(error => {
      component.loading = false;
      component.showError('Error fetching editing information', component.getError(error));
    });
  },
  methods: {
    save: function() {
      this.loading = true;
      let editableObject = this.makeCopy(this.editableObject);
      let component = this;
      editableObject['notes'] = editableObject['notes'].trim();
      let httpRequest;
      if (this.creatingNew) {
        httpRequest = axios.put('api/campaigns/create', editableObject)
      } else {
        httpRequest = axios.post('api/campaigns/update', editableObject)
      }
      httpRequest.then(response => {
        component.loading = false;
        window.location = 'campaigns?prepid=' + response.data.response.prepid;
      }).catch(error => {
        component.loading = false;
        component.showError('Error saving campaign', component.getError(error));
      });
    },
    cancel: function() {
      if (this.creatingNew) {
        window.location = 'campaigns';
      } else {
        window.location = 'campaigns?prepid=' + this.prepid;
      }
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
    }
  }
}
</script>