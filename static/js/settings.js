document.addEventListener('DOMContentLoaded', function() {
    const listItems = document.querySelectorAll('.list-group-item');
    listItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            listItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');
            const target = this.getAttribute('data-target');
            document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('show', 'active'));
            document.querySelector(target).classList.add('show', 'active');
        });
    });
});

