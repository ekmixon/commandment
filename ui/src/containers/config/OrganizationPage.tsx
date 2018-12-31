import * as React from "react";
import { connect, Dispatch } from "react-redux";
import {RouteComponentProps} from "react-router";
import {Link} from "react-router-dom";
import {bindActionCreators} from "redux";
import {IOrganizationFormValues, OrganizationForm} from "../../components/forms/OrganizationForm";
import {RSAAApiErrorMessage} from "../../components/RSAAApiErrorMessage";
import {RootState} from "../../reducers/index";
import * as actions from "../../store/organization/actions";
import {OrganizationState} from "../../store/organization/reducer";

import Breadcrumb from "semantic-ui-react/dist/commonjs/collections/Breadcrumb/Breadcrumb";
import Container from "semantic-ui-react/src/elements/Container";
import Header from "semantic-ui-react/src/elements/Header";

interface OrganizationPageState {
    organization: OrganizationState;
}

function mapStateToProps(state: RootState, ownProps?: any): OrganizationPageState {
    return {
        organization: state.organization,
    }
}

interface OrganizationPageDispatchProps {
    read: actions.ReadActionRequest;
    post: actions.PostActionRequest;
}

function mapDispatchToProps(dispatch: Dispatch<any>) {
    return bindActionCreators({
        post: actions.post,
        read: actions.read,
    }, dispatch);
}

interface OrganizationPageProps extends OrganizationPageState, OrganizationPageDispatchProps, RouteComponentProps<any> {

}

export class UnconnectedOrganizationPage extends React.Component<OrganizationPageProps, undefined> {

    public componentWillMount?() {
        this.props.read();
    }

    private handleSubmit: (values: IOrganizationFormValues) => void = (values) => {
        this.props.post(values);
    };

    public render(): JSX.Element {
        const {
            organization,
        } = this.props;

        return (
            <Container className="OrganizationPage">
                <Breadcrumb>
                    <Breadcrumb.Section><Link to={`/`}>Home</Link></Breadcrumb.Section>
                    <Breadcrumb.Divider />
                    <Breadcrumb.Section><Link to={`/settings`}>Settings</Link></Breadcrumb.Section>
                    <Breadcrumb.Divider />
                    <Breadcrumb.Section active>Organization</Breadcrumb.Section>
                </Breadcrumb>

                <Header as="h1">Organization</Header>
                <p>Many parts of the system rely on showing your organization name in certain user facing scenarios.
                    Configure these details here</p>
                {organization.error && <RSAAApiErrorMessage error={organization.errorDetail} />}
                {organization.organization &&
                    <OrganizationForm
                        loading={organization.loading}
                        isSubmitting={organization.loading}
                        data={organization.organization}
                        id={organization.organization.id}
                        onSubmit={this.handleSubmit}
                    />}

            </Container>
        )
    }

}

export const OrganizationPage = connect<OrganizationPageState, OrganizationPageDispatchProps, OrganizationPageProps>(
    mapStateToProps,
    mapDispatchToProps,
)(UnconnectedOrganizationPage);
