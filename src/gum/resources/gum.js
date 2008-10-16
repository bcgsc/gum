function updateGroupMembers(view_url, value) {
    new Ajax.Updater(
        document.getElementById('groupmembers'),
        view_url,
        { method:'post',
          parameters: {'gid': value,}, }
    );
}
