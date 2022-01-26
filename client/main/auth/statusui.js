
'use strict';


class AuthStatusUI extends HTMLElement {

    constructor() {
        super();

        this._root = this.attachShadow({ mode: 'open' });
        this._host = this._root.host;

        let css = document.createElement('style');
        css.innerText = this._css();
        this._root.appendChild(css);

        let status = document.createElement('div');
        status.id = 'status';

        let circle = document.createElement('div');
        circle.id = 'circle';
        status.appendChild(circle);

        this._root.appendChild(status);

        let dropDown = document.createElement('div');
        dropDown.id = 'dropdown';

        let top = document.createElement('div');
        top.id = 'top';

        let plan = document.createElement('div');
        plan.id = 'plan';
        plan.innerText = 'Guest plan';
        top.appendChild(plan);

        let signInOut = document.createElement('button');
        signInOut.innerText = 'Sign out';
        top.appendChild(signInOut);

        dropDown.appendChild(top);


        let bottom = document.createElement('div');
        bottom.id = 'bottom';

        let bigCircle = document.createElement('div');
        bigCircle.id = 'big-circle';
        bottom.appendChild(bigCircle);

        let userInfo = document.createElement('div');
        userInfo.id = 'user-info';

        let name = document.createElement('div');
        name.id = 'name';
        name.innerText = 'Guest';
        userInfo.appendChild(name);

        let email = document.createElement('div');
        email.id = 'email';
        email.innerText = 'jon@thon.cc';
        userInfo.appendChild(email);

        bottom.appendChild(userInfo);

        dropDown.appendChild(bottom);

        this._root.appendChild(dropDown);

        this._dropDownVisible = false;
        status.addEventListener('click', () => {
            if ( ! this._dropDownVisible) {
                dropDown.classList.add('show');
                this._dropDownVisible = true;
            }
            else {
                dropDown.classList.remove('show');
                this._dropDownVisible = false;
            }

        });
    }

    _css() {
        return `
            :host {
                position: absolute ;
                width: 60px ;
                height: 34px ;
                right: 64px ;
                top: 0px ;
                color: #333333 ;
            }

            #status:hover {
                background-color: #4675B1 ;
            }

            #circle {
                background-color: lightblue ;
                margin: 2px ;
                width: 30px ;
                height: 30px ;
                border-radius: 15px ;
            }

            #dropdown {
                background-color: white ;
                width: 300px ;
                height: 120px ;
                position: absolute ;
                right: 0px ;
                z-index: 50 ;
                display: flex ;
                flex-direction: column ;
                padding: 6px ;
                box-shadow: 0 24px 54px ;
                transition: all .1s ;

                visibility: hidden ;
                pointer-events: none ;
                opacity: 0 ;
            }

            #dropdown.show {
                visibility: visible ;
                pointer-events: auto ;
                opacity: 1 ;
            }

            #top {
                display: flex ;
                flex-direction: row ;
            }

            #plan {
                padding: 6px ;
                flex: 1 ;
            }

            #bottom {
                display: flex ;
                padding: 6px ;
            }

            #name {
                flex: 1 ;
                font-size: 140% ;
                margin-bottom: 6px ;
            }

            #big-circle {
                width: 80px ;
                height: 80px ;
                border-radius: 50% ;
                background-color: lightblue ;
            }

            #user-info {
                margin-left: 20px ;
            }

        `;
    }

}

customElements.define('jmv-authstatusui', AuthStatusUI);
