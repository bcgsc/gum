function createNamedElement(name) {
   var element = null;
   try {
       // Internet Explorer needs special way of creating this element
       element = document.createElement('<input name="'+name+'">');
   } catch (e) {}
   if (!element || element.nodeName != 'INPUT') {
       element = document.createElement('input');
       element.name = name;
   }
   return element;
}

function rebuildValues(field_id) {
    var counter = 0;
    found = document.getElementById('value.'+counter+'.'+field_id);
    while (found != null) {
        found.parentNode.removeChild(found);
        counter++;
        found = document.getElementById('value.'+counter+'.'+field_id);
    }

    var select = document.getElementById('select.'+field_id);
    var source = document.getElementById(field_id);
    var sourceParent = source.parentNode;
    for (var x = 0; x < select.options.length; x++) {
        copy = createNamedElement(field_id);
        copy.setAttribute('type', 'hidden');
        copy.setAttribute('id', 'value.'+x+'.'+field_id);
        copy.setAttribute('value', select.options[x].value);
        sourceParent.insertBefore(copy, source);
    }
}

function sequenceAddItem(field_id) {
    var input = document.getElementById('input.'+field_id);
    if (input.value.length > 0) {
        var select = document.getElementById('select.'+field_id);
        var item = new Option(input.value, input.value);
        select.options[select.length] = item;
        rebuildValues(field_id);
    }
    input.value = '';
}

function sequenceRemoveItem(field_id) {
    var select = document.getElementById('select.'+field_id);
    if (select.selectedIndex >= 0) {
        select.remove(select.selectedIndex);
        rebuildValues(field_id);
    }
}

function sequenceAddClicked(field_id, value) {
    var select = document.getElementById('select.'+field_id);
    var item = new Option(value, value);
    select.options[select.length] = item;
    rebuildValues(field_id);
}