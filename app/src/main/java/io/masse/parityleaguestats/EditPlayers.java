package io.masse.parityleaguestats;

import android.app.Activity;
import android.content.Intent;
import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.os.Bundle;
import android.text.InputType;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.AutoCompleteTextView;
import android.widget.Button;
import android.widget.TextView;

import io.masse.parityleaguestats.customLayout.customLinearLayout;
import io.masse.parityleaguestats.model.Gender;
import io.masse.parityleaguestats.model.Team;
import io.masse.parityleaguestats.model.Teams;

public class EditPlayers extends Activity {
    TextView leftTeamName, rightTeamName;
    private customLinearLayout layoutLeft;
    private customLinearLayout layoutRight;
    private Button btnLastButtonClicked;
    private View.OnClickListener teamEditListener;
    private Context context;

    private Teams teams;
    private Team leftTeam;
    private Team rightTeam;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_edit_players);

        context = this;

        loadIntent();
        initViewVariables();
        bindEvents();
        redraw();
    }

    private void loadIntent() {
        teams = (Teams) this.getIntent().getSerializableExtra("teams");
        leftTeam = (Team) this.getIntent().getSerializableExtra("leftTeam");
        rightTeam = (Team) this.getIntent().getSerializableExtra("rightTeam");
    }

    private void initViewVariables() {
        leftTeamName = (TextView) findViewById(R.id.leftTeam);
        rightTeamName = (TextView) findViewById(R.id.rightTeam);

        layoutLeft = (customLinearLayout) findViewById(R.id.layoutLeftNames);
        layoutRight = (customLinearLayout) findViewById(R.id.layoutRightNames);
    }

    private void bindEvents() {
        teamEditListener = new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                btnLastButtonClicked = (Button) view;
                String deleteTxt = "Delete " + btnLastButtonClicked.getText();

                new AlertDialog.Builder(context)
                        .setTitle("Edit")
                        .setItems(new String[]{ deleteTxt, "Cancel" },
                            new DialogInterface.OnClickListener() {
                                public void onClick(DialogInterface dialog, int which) {
                                switch (which) {
                                    case 0: //delete player
                                        String playerName = btnLastButtonClicked.getText().toString();
                                        Boolean isMale = btnLastButtonClicked.getTag() == Gender.Male;
                                        if (btnLastButtonClicked.getParent() == layoutLeft) {
                                            leftTeam.removePlayer(playerName, isMale);
                                            redraw();
                                        } else {
                                            rightTeam.removePlayer(playerName, isMale);
                                            redraw();
                                        }
                                        break;
                                    case 1: //do nothing
                                        break;
                                }
                                }
                            }).show();
            }
        };



        final Button editButton = (Button) findViewById(R.id.btnAddPlayer);
        editButton.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
            final AutoCompleteTextView input = new AutoCompleteTextView(v.getContext());
            input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PERSON_NAME | InputType.TYPE_TEXT_FLAG_CAP_WORDS);

            final String[] teams = new String[] {
                leftTeam.name,
                rightTeam.name
            };

            new AlertDialog.Builder(context)
                .setTitle("Choose Team")
                .setItems(teams, new DialogInterface.OnClickListener() {
                    public void onClick(DialogInterface dialog, int which) {
                        switch (which) {
                            case 0:
                                addSubstitutePlayer(input, leftTeam);
                                break;
                            case 1:
                                addSubstitutePlayer(input, rightTeam);
                                break;
                        }
                    }
                }).show();
            }
        });


        final Button finishButton = (Button) findViewById(R.id.btnFinish);
        finishButton.setOnClickListener(new View.OnClickListener() {
                                            public void onClick(View v) {
                                                Intent intent = new Intent(context, Roster.class);
                                                Bundle bundle = new Bundle();
                                                bundle.putSerializable("teams", teams);
                                                bundle.putSerializable("leftTeam", leftTeam);
                                                bundle.putSerializable("rightTeam", rightTeam);
                                                intent.putExtras(bundle);
                                                startActivity(intent);
                                            }
                                        });
    }

    private void addSubstitutePlayer(final AutoCompleteTextView input, final Team team) {
        input.setAdapter(new ArrayAdapter<>(
            context,
            android.R.layout.simple_dropdown_item_1line,
            teams.allPlayers())
        );

        new AlertDialog.Builder(context)
            .setTitle("Add Substitute Player")
            .setMessage("Player Name")
            .setView(input)
            .setPositiveButton("Ok", new DialogInterface.OnClickListener() {
                public void onClick(DialogInterface dialog, int whichButton) {
                final String playerName = input.getText().toString() + "(S)";

                final Gender gender = teams.getPlayerGender(playerName);
                if (gender == Gender.Unknown) {
                    new AlertDialog.Builder(context)
                        .setTitle("Select Gender")
                        .setMessage(playerName)
                        .setPositiveButton("Female", new DialogInterface.OnClickListener() {
                            @Override
                            public void onClick(DialogInterface dialogInterface, int i) {
                                team.addPlayer(playerName, Gender.Female);
                                redraw();
                            }
                        })
                        .setNegativeButton("Male", new DialogInterface.OnClickListener() {
                            @Override
                            public void onClick(DialogInterface dialogInterface, int i) {
                                team.addPlayer(playerName, Gender.Male);
                                redraw();
                            }
                        }).show();
                } else {
                    team.addPlayer(playerName, gender);
                    redraw();
                }

                }
            }).setNegativeButton("Cancel", new DialogInterface.OnClickListener() {
                public void onClick(DialogInterface dialog, int whichButton) {
                    // Do nothing.
                }
            }).show();
    }

    private void redraw() {
        leftTeamName.setText(leftTeam.name);
        Utils.draw_players(context, layoutLeft, teamEditListener, leftTeam, true);

        rightTeamName.setText(rightTeam.name);
        Utils.draw_players(context, layoutRight, teamEditListener, rightTeam, false);
    }
}
