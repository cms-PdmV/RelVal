<template>
  <div>
    <h1 v-if="creatingNew">Creating new Ticket</h1>
    <h1 v-else>Editing {{editableObject.prepid}}</h1>
    <v-card raised class="editPageCard">
      <table v-if="editableObject">
        <tr>
          <td>PrepID</td>
          <td><input type="text" v-model="editableObject.prepid" :disabled="!editingInfo.prepid"></td>
        </tr>
        <tr>
          <td>CMSSW Release</td>
          <td><input type="text" v-model="editableObject.cmssw_release" :disabled="!editingInfo.cmssw_release"></td>
        </tr>
        <tr>
          <td>Conditions GlobalTag</td>
          <td><input type="text" v-model="editableObject.conditions_globaltag" :disabled="!editingInfo.conditions_globaltag"></td>
        </tr>
        <tr>
          <td>Extension Number</td>
          <td><input type="number" v-model="editableObject.extension_number" :disabled="!editingInfo.extension_number"></td>
        </tr>
        <tr>
          <td>High Statistics</td>
          <td><v-checkbox v-model="editableObject.high_statistics" :disabled="!editingInfo.high_statistics" hide-details class="shrink checkbox-margin"></v-checkbox></td>
        </tr>
        <tr>
          <td>Notes</td>
          <td><textarea v-model="editableObject.notes" :disabled="!editingInfo.notes"></textarea></td>
        </tr>
        <tr>
          <td>Processing String</td>
          <td><input type="text" v-model="editableObject.processing_string" :disabled="!editingInfo.processing_string"></td>
        </tr>
        <tr>
          <td>Reuse GEN-SIM</td>
          <td><v-checkbox v-model="editableObject.reuse_gensim" :disabled="!editingInfo.reuse_gensim" hide-details class="shrink checkbox-margin"></v-checkbox></td>
        </tr>
        <tr>
          <td>Sample Tag</td>
          <td><input type="text" v-model="editableObject.sample_tag" :disabled="!editingInfo.sample_tag"></td>
        </tr>
      </table>
      <v-btn small class="mr-1 mb-1" color="primary" @click="save()">Save</v-btn>
    </v-card>
    <v-overlay :absolute="false"
               :opacity="0.95"
               :z-index="3"
               :value="loading"
               style="text-align: center">
      <v-progress-circular indeterminate color="primary"></v-progress-circular>
      <br>Please wait...
    </v-overlay>
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
export default {
  components: {
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
    this.loading = true;
    let query = Object.assign({}, this.$route.query);
    this.prepid = query['prepid'];
    this.creatingNew = this.prepid === undefined;
    let component = this;
    axios.get('api/tickets/get_editable' + (this.creatingNew ? '' : ('/' + this.prepid))).then(response => {
      component.editableObject = response.data.response.object;
      component.editingInfo = response.data.response.editing_info;
      component.loading = false;
    });
  },
  methods: {
    save: function() {
      let editableObject = JSON.parse(JSON.stringify(this.editableObject))
      let component = this;
      editableObject['notes'] = editableObject['notes'].trim();
      let httpRequest;
      this.loading = true;
      if (this.creatingNew) {
        httpRequest = axios.put('api/tickets/create', editableObject)
      } else {
        httpRequest = axios.post('api/tickets/update', editableObject)
      }
      httpRequest.then(response => {
        component.loading = false;
        window.location = 'tickets?prepid=' + response.data.response.prepid;
      }).catch(error => {
        component.loading = false;
        this.showError('Error saving ticket', error.response.data.message)
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
    listLength(l) {
      if (!l) {
        return 0;
      }
      return l.split('\n').filter(Boolean).length;
    },
  }
}
</script>

<style scoped>
h1 {
  margin: 8px;
}
td {
  padding-top: 8px;
  padding-bottom: 8px;
  padding-right: 4px;
}
.editPageCard {
  margin: auto;
  padding: 16px;
  max-width: 750px;
}
.checkbox-margin {
  margin: 0 !important;
  padding: 0 !important;
}
</style>